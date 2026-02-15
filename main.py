"""
Main entry point for AI Content Telegram Bot with subscription support.

This version includes fixes:
- BOT_TOKEN validation on startup
- Single-instance protection via InstanceLock + process scan
- Robust user registration using register_or_get_user (handles concurrent inserts)
- Correct PollingManager instantiation
- Safe shutdown_manager invocation and registration of instance_lock.release
- Guarded stats tracking to avoid AttributeError when stats methods missing
"""

import asyncio
import os
import re
from typing import Optional

from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Custom modules
from config import config
from logger_config import logger
from api_client import api_client, PerplexityAPIError
from translation_service import translation_service
from rag_service import rag_service

# Database init
from database import init_db

# Handlers / middlewares
from handlers import subscription_router
from middlewares import SubscriptionMiddleware

# Services (use register_or_get_user to avoid race conditions)
from services.user_service import (
    register_or_get_user,
    is_premium,
    count_premium,
    get_user,
)
from database.models import User, UserRole

# Utils
from utils import (
    setup_expiration_job,
    InstanceLock,
    is_another_instance_running,
    shutdown_manager,
    PollingManager,
)

# Optional components
try:
    from bot_statistics import stats_tracker, BotStatistics
    STATS_ENABLED = True
    logger.info("✅ Statistics tracking enabled")
except Exception:
    STATS_ENABLED = False
    stats_tracker = None
    logger.warning("⚠️ bot_statistics module not available")

try:
    from services.image_fetcher import ImageFetcher
    image_fetcher = ImageFetcher(
        pexels_key=config.pexels_api_key,
        pixabay_key=config.pixabay_api_key,
    )
    IMAGES_ENABLED = bool(config.pexels_api_key or config.pixabay_api_key)
    if IMAGES_ENABLED:
        logger.info(f"✅ Image fetcher enabled (Pexels: {bool(config.pexels_api_key)}, Pixabay: {bool(config.pixabay_api_key)})")
    else:
        logger.warning("⚠️ Image fetcher available but no API keys configured")
except Exception:
    IMAGES_ENABLED = False
    image_fetcher = None
    logger.warning("⚠️ image_fetcher module not available")

# Admins
ADMIN_USER_IDS = config.admin_user_ids or []

# Startup logs
logger.info("=" * 60)
logger.info("AI Content Telegram Bot v3.0 Starting (with Subscriptions)...")
logger.info("=" * 60)
config_info = config.get_safe_config_info()
logger.info(f"Configuration loaded: {config_info}")

from rag_service import RAG_ENABLED
if not RAG_ENABLED:
    logger.info("RAG Status: DISABLED (via RAG_ENABLED=false)")
elif rag_service.is_enabled():
    logger.info("RAG Status: ENABLED ✅")
else:
    logger.info("RAG Status: DISABLED (dependencies not installed - see requirements-rag.txt)")

logger.info(f"Translation Status: {'ENABLED' if translation_service.is_enabled() else 'DISABLED'}")
logger.info(f"Images Status: {'ENABLED' if IMAGES_ENABLED else 'DISABLED'}")
logger.info(f"Statistics Status: {'ENABLED' if STATS_ENABLED else 'DISABLED'}")
logger.info(f"Payments Status: {'ENABLED' if config.provider_token else 'DISABLED'}")
logger.info(f"Admin Users: {len(ADMIN_USER_IDS)}")


# Validate BOT_TOKEN before creating Bot instance to fail fast with clear message
def _validate_bot_token(token: Optional[str]) -> str:
    if not token:
        logger.error("BOT_TOKEN is empty. Please set BOT_TOKEN environment variable.")
        raise SystemExit("Missing BOT_TOKEN")
    token = token.strip()
    if not re.match(r'^\d+:[A-Za-z0-9_-]+$', token):
        logger.error(
            "BOT_TOKEN appears to have a wrong format. Ensure you pasted the BotFather token exactly "
            "(no quotes, no 'Bot ' prefix)."
        )
        raise SystemExit("Invalid BOT_TOKEN format")
    return token


validated_token = _validate_bot_token(config.bot_token)

# Initialize bot and dispatcher
bot = Bot(token=validated_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

# Scheduler placeholder
scheduler: Optional[AsyncIOScheduler] = None

# Routers and middleware
dp.include_router(subscription_router)
dp.message.middleware(SubscriptionMiddleware(premium_commands=[]))


# FSM States
class PostGeneration(StatesGroup):
    waiting_for_topic = State()
    post_type = State()  # "text" or "images"


# Keyboards
kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📝 Пост"), KeyboardButton(text="🖼️ Пост с фото")],
        [KeyboardButton(text="❓ Помощь"), KeyboardButton(text="ℹ️ Статус")],
    ],
    resize_keyboard=True,
)
kb_admin = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📝 Пост"), KeyboardButton(text="🖼️ Пост с фото")],
        [KeyboardButton(text="❓ Помощь"), KeyboardButton(text="ℹ️ Статус")],
        [KeyboardButton(text="📊 Статистика")],
    ],
    resize_keyboard=True,
)


def get_keyboard(user_id: int) -> ReplyKeyboardMarkup:
    return kb_admin if user_id in ADMIN_USER_IDS else kb


async def generate_content(topic: str, user_id: int = None) -> str:
    try:
        # Stats tracking (guarded)
        if STATS_ENABLED and stats_tracker and user_id:
            if hasattr(stats_tracker, "track_generation"):
                try:
                    maybe = stats_tracker.track_generation
                    if asyncio.iscoroutinefunction(maybe):
                        await maybe(user_id, topic)
                    else:
                        maybe(user_id, topic)
                except Exception:
                    logger.exception("Failed to track generation (stats_tracker.track_generation)")
            else:
                logger.warning("Stats tracker missing 'track_generation' method — skipping stats recording")

        # RAG context fetch
        rag_context = None
        if rag_service.is_enabled():
            rag_context = await rag_service.get_context(topic)

        content = await api_client.generate_content(topic, rag_context=rag_context)

        # Language detection + translation if needed
        is_russian = translation_service.detect_language(content)
        if is_russian and translation_service.is_enabled():
            content = translation_service.translate_to_english(content)

        return content
    except PerplexityAPIError as e:
        logger.error(f"Content generation failed: {e}")
        return "❌ Не удалось сгенерировать контент. Попробуйте позже."
    except Exception as e:
        logger.exception(f"Unexpected error during content generation: {e}")
        return "❌ Произошла ошибка. Пожалуйста, попробуйте снова."


@dp.message(CommandStart())
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    logger.info(f"User {user_id} started the bot")

    # Use register_or_get_user to avoid race conditions on insert
    try:
        user = await register_or_get_user(
            telegram_id=user_id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
            role=UserRole.USER,
        )
        if user:
            logger.info(f"Registered/loaded user {user_id} in database")
    except Exception:
        logger.exception("Error registering or retrieving user")

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
        reply_markup=get_keyboard(user_id),
    )


async def _call_shutdown_manager(sm):
    """
    Helper to safely call shutdown_manager which may be an object with shutdown()
    or a callable/coroutine.
    """
    if sm is None:
        logger.warning("No shutdown_manager provided; skipping shutdown")
        return
    if callable(sm) and not hasattr(sm, "shutdown"):
        if asyncio.iscoroutinefunction(sm):
            await sm()
        else:
            sm()
        return
    if hasattr(sm, "shutdown"):
        method = getattr(sm, "shutdown")
        if asyncio.iscoroutinefunction(method):
            await method()
        else:
            method()
        return
    logger.error("shutdown_manager is not callable and has no 'shutdown' method; skipping explicit shutdown call")


async def main() -> None:
    global scheduler

    # --- Instance lock: ensure single running bot instance ---
    instance_lock = InstanceLock()  # defaults to /tmp/telegram_bot.lock

    try:
        if is_another_instance_running():
            logger.error("Another bot instance detected by process scan — aborting startup")
            raise SystemExit(1)
    except Exception:
        logger.warning("Process scan for other instances failed; will rely on PID file lock")

    if not instance_lock.acquire():
        logger.error("Failed to acquire instance lock — another instance may be running. Exiting.")
        raise SystemExit(1)

    # Register release() on graceful shutdown
    try:
        shutdown_manager.register_callback(instance_lock.release)
    except Exception:
        logger.warning("Could not register instance_lock.release with shutdown_manager; atexit will still attempt release")
    # --- end instance lock block ---

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

    # Instantiate PollingManager correctly (do not pass logger as positional arg)
    polling_manager = PollingManager(max_retries=5, initial_delay=5.0, max_delay=300.0, backoff_factor=2.0)

    try:
        logger.info("🚀 Starting bot polling (attempt 1/6)...")
        await polling_manager.start_polling_with_retry(dp, bot, on_conflict_callback=None)
    finally:
        # Ensure graceful shutdown — call shutdown_manager safely
        await _call_shutdown_manager(shutdown_manager)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down due to interrupt/exit")
