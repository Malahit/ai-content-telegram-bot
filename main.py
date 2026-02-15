"""
Main entry point for AI Content Telegram Bot with subscription support.
This is the new main file that includes subscription and payment functionality.
For backward compatibility, bot.py is still available but this file should be used
for running the bot with subscription features.
"""

import asyncio
import os
import random
import re
import sys
from typing import Optional

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart, Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InputMediaPhoto
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Import custom modules
from config import config
from logger_config import logger
from api_client import api_client, PerplexityAPIError
from translation_service import translation_service
from rag_service import rag_service

# Import database
from database import init_db

# Import handlers and middlewares
from handlers import subscription_router
from middlewares import SubscriptionMiddleware

# Import services
from services.user_service import is_premium, count_premium, get_user, add_user
from database.models import User

# Import utils
from utils import setup_expiration_job, InstanceLock, is_another_instance_running, shutdown_manager, PollingManager

# Import statistics and image fetcher from main
try:
    from bot_statistics import stats_tracker, BotStatistics
    STATS_ENABLED = True
    logger.info("✅ Statistics tracking enabled")
except ImportError:
    STATS_ENABLED = False
    stats_tracker = None
    logger.warning("⚠️ bot_statistics module not available")

try:
    from services.image_fetcher import ImageFetcher
    # Initialize with both API keys
    image_fetcher = ImageFetcher(
        pexels_key=config.pexels_api_key,
        pixabay_key=config.pixabay_api_key
    )
    # Images are enabled if at least one API key is configured
    IMAGES_ENABLED = bool(config.pexels_api_key or config.pixabay_api_key)
    if IMAGES_ENABLED:
        logger.info(f"✅ Image fetcher enabled (Pexels: {bool(config.pexels_api_key)}, Pixabay: {bool(config.pixabay_api_key)})")
    else:
        logger.warning("⚠️ Image fetcher available but no API keys configured")
except ImportError:
    IMAGES_ENABLED = False
    image_fetcher = None
    logger.warning("⚠️ image_fetcher module not available")

# Get admin user IDs from config
ADMIN_USER_IDS = config.admin_user_ids

# Log startup information (without sensitive data)
logger.info("=" * 60)
logger.info("AI Content Telegram Bot v3.0 Starting (with Subscriptions)...")
logger.info("=" * 60)

config_info = config.get_safe_config_info()
logger.info(f"Configuration loaded: {config_info}")

# Enhanced RAG status logging - import RAG_ENABLED from rag_service to avoid duplication
from rag_service import RAG_ENABLED
if not RAG_ENABLED:
    logger.info(f"RAG Status: DISABLED (via RAG_ENABLED=false)")
elif rag_service.is_enabled():
    logger.info(f"RAG Status: ENABLED ✅")
else:
    logger.info(f"RAG Status: DISABLED (dependencies not installed - see requirements-rag.txt)")
    
logger.info(f"Translation Status: {'ENABLED' if translation_service.is_enabled() else 'DISABLED'}")
logger.info(f"Images Status: {'ENABLED' if IMAGES_ENABLED else 'DISABLED'}")
logger.info(f"Statistics Status: {'ENABLED' if STATS_ENABLED else 'DISABLED'}")
logger.info(f"Payments Status: {'ENABLED' if config.provider_token else 'DISABLED'}")
logger.info(f"Admin Users: {len(ADMIN_USER_IDS)}")


# Validate BOT_TOKEN before creating Bot instance to fail fast with clear message
def _validate_bot_token(token: Optional[str]) -> str:
    import re
    if not token:
        logger.error("BOT_TOKEN is empty. Please set BOT_TOKEN environment variable.")
        raise SystemExit("Missing BOT_TOKEN")
    token = token.strip()
    if not re.match(r'^\d+:[A-Za-z0-9_-]+$', token):
        logger.error("BOT_TOKEN appears to have a wrong format. Ensure you pasted the BotFather token exactly (no quotes, no 'Bot ' prefix).")
        raise SystemExit("Invalid BOT_TOKEN format")
    return token

validated_token = _validate_bot_token(config.bot_token)

# Initialize bot and dispatcher
bot = Bot(
    token=validated_token,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher(storage=MemoryStorage())

# Global scheduler instance
scheduler: Optional[AsyncIOScheduler] = None

# Include subscription router
dp.include_router(subscription_router)

# Add subscription middleware for premium-only commands
dp.message.middleware(SubscriptionMiddleware(premium_commands=[]))

# FSM States for post generation
class PostGeneration(StatesGroup):
    waiting_for_topic = State()
    post_type = State()  # "text" or "images"

# Main keyboard for all users
kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📝 Пост"), KeyboardButton(text="🖼️ Пост с фото")],
        [KeyboardButton(text="❓ Помощь"), KeyboardButton(text="ℹ️ Статус")]
    ],
    resize_keyboard=True,
)

# Admin keyboard with statistics button
kb_admin = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📝 Пост"), KeyboardButton(text="🖼️ Пост с фото")],
        [KeyboardButton(text="❓ Помощь"), KeyboardButton(text="ℹ️ Статус")],
        [KeyboardButton(text="📊 Статистика")]
    ],
    resize_keyboard=True,
)


def get_keyboard(user_id: int) -> ReplyKeyboardMarkup:
    return kb_admin if user_id in ADMIN_USER_IDS else kb


async def generate_content(topic: str, user_id: int = None) -> str:
    try:
        # Track content generation request (guarded — won't break generation if stats not available)
        if STATS_ENABLED and stats_tracker and user_id:
            if hasattr(stats_tracker, "track_generation"):
                try:
                    # If track_generation is async in your implementation, adjust accordingly
                    stats_tracker.track_generation(user_id, topic)
                except Exception:
                    logger.exception("Failed to track generation (stats_tracker.track_generation)")
            else:
                logger.warning("Stats tracker missing 'track_generation' method — skipping stats recording")

        # Get RAG context if enabled
        rag_context = None
        if rag_service.is_enabled():
            rag_context = await rag_service.get_context(topic)

        # Generate content using API
        content = await api_client.generate_content(topic, rag_context=rag_context)

        # Detect language
        is_russian = translation_service.detect_language(content)

        # Translate to English if content is in Russian and translation is enabled
        if is_russian and translation_service.is_enabled():
            content = translation_service.translate_to_english(content)

        return content
    except PerplexityAPIError as e:
        logger.error(f"Content generation failed: {e}")
        return f"❌ Не удалось сгенерировать контент. Попробуйте позже."
    except Exception as e:
        logger.exception(f"Unexpected error during content generation: {e}")
        return f"❌ Произошла ошибка. Пожалуйста, попробуйте снова."


@dp.message(CommandStart())
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    logger.info(f"User {user_id} started the bot")

    # Ensure user exists in database
    user = await get_user(user_id)
    if not user:
        user = User(
            telegram_id=user_id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name
        )
        await add_user(user)
        logger.info(f"Registered new user {user_id} in database")

    rag_status = "✅ RAG" if rag_service.is_enabled() else "⚠️ Без RAG"
    translate_status = "🌐 RU/EN" if translation_service.is_enabled() else ""
    images_status = "🖼️ Images" if IMAGES_ENABLED else ""

    user_is_premium = await is_premium(user_id)
    premium_badge = " 🌟" if user_is_premium else ""

    await message.answer(
        f"<b>🚀 AI Content Bot v3.0{premium_badge} {rag_status} {translate_status} {images_status}</b>\n\n"
        f"💬 <i>Тема поста → готовый текст 200-300 слов!</i>\n\n"
        f"📡 Автопостинг: <code>{config.channel_id}</code> (каждые {config.autopost_interval_hours}ч)\n"
        f"⚙️ max_tokens={config.max_tokens} | {config.api_model}\n\n"
        f"<b>Примеры:</b> SMM Москва | фитнес | завтрак\n\n"
        f"💎 <b>Premium:</b> /subscribe - Получить премиум доступ",
        reply_markup=get_keyboard(user_id)
    )

# ... Остальная логика main.py (обработчики, init_db вызов, polling manager и т.д.)
# Внимание: ниже приведён вызов стартовой логики — убедитесь, что у вас в проекте
# остальной код (polling_manager, setup jobs, handlers) как в оригинальном main.py.

async def main() -> None:
    global scheduler
    # Initialize DB
    try:
        await init_db()
        logger.info("✅ Database initialized")
    except Exception:
        logger.exception("Failed to initialize database")

    # Scheduler and jobs
    scheduler = AsyncIOScheduler()
    setup_expiration_job(scheduler)
    scheduler.start()
    logger.info("✅ Scheduler started")

    # Start polling with graceful shutdown handlers (PollingManager реализован в utils)
    # instantiate PollingManager — используем именованный аргумент, чтобы не сдвинуть позиционные параметры
try:
    polling_manager = PollingManager(logger=logger)
except TypeError:
    # Если PollingManager старой версии ожидает logger как первый позиционный аргумент,
    # используем fallback, но это должно быть безопасно.
        # Instantiate PollingManager — используем именованный аргумент
    try:
        polling_manager = PollingManager(logger=logger)
    except TypeError:
        polling_manager = PollingManager(logger)

    try:
        logger.info("🚀 Starting bot polling (attempt 1/6)...")
        await polling_manager.start_polling_with_retry(dp, bot, on_conflict_callback=None)
    finally:
        # Ensure graceful shutdown — вызываем безопасно
        async def _call_shutdown_manager(sm):
            if callable(sm):
                if asyncio.iscoroutinefunction(sm):
                    await sm()
                else:
                    sm()
            elif hasattr(sm, "shutdown"):
                method = getattr(sm, "shutdown")
                if asyncio.iscoroutinefunction(method):
                    await method()
                else:
                    method()
            else:
                logger.error("shutdown_manager is not callable and has no 'shutdown' method; skipping explicit shutdown call")

        await _call_shutdown_manager(shutdown_manager)
