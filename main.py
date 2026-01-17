"""
Main entry point for AI Content Telegram Bot with subscription support.

This is the new main file that includes subscription and payment functionality.
For backward compatibility, bot.py is still available but this file should be used
for running the bot with subscription features.
"""

import asyncio
import random
import re
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
from utils import setup_expiration_job

# Import statistics and image fetcher from main
try:
    from bot_statistics import stats_tracker
    STATS_ENABLED = True
    logger.info("✅ Statistics tracking enabled")
except ImportError:
    STATS_ENABLED = False
    stats_tracker = None
    logger.warning("⚠️ bot_statistics module not available")

try:
    from image_fetcher import ImageFetcher
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
logger.info(f"RAG Status: {'ENABLED' if rag_service.is_enabled() else 'DISABLED'}")
logger.info(f"Translation Status: {'ENABLED' if translation_service.is_enabled() else 'DISABLED'}")
logger.info(f"Images Status: {'ENABLED' if IMAGES_ENABLED else 'DISABLED'}")
logger.info(f"Statistics Status: {'ENABLED' if STATS_ENABLED else 'DISABLED'}")
logger.info(f"Payments Status: {'ENABLED' if config.provider_token else 'DISABLED'}")
logger.info(f"Admin Users: {len(ADMIN_USER_IDS)}")


# Initialize bot and dispatcher
bot = Bot(
    token=config.bot_token,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher(storage=MemoryStorage())

# Include subscription router
dp.include_router(subscription_router)

# Add subscription middleware for premium-only commands
# For now, we don't restrict any existing commands, but /generate will be premium-only
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
    """
    Get keyboard based on user role.
    
    Args:
        user_id: Telegram user ID
        
    Returns:
        ReplyKeyboardMarkup: Keyboard for the user
    """
    return kb_admin if user_id in ADMIN_USER_IDS else kb


async def generate_content(topic: str, user_id: int = None) -> str:
    """
    Generate content using Perplexity API with optional RAG and translation.
    
    Args:
        topic: Topic to generate content about
        user_id: Optional user ID for statistics tracking
        
    Returns:
        str: Generated content
    """
    try:
        # Track content generation request
        if STATS_ENABLED and stats_tracker and user_id:
            stats_tracker.track_generation(user_id, topic)
        
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
        logger.error(f"Unexpected error during content generation: {e}", exc_info=True)
        return f"❌ Произошла ошибка. Пожалуйста, попробуйте снова."


@dp.message(CommandStart())
async def start_handler(message: types.Message):
    """
    Handle /start command.
    
    Sends welcome message with bot information and usage instructions.
    Also ensures user is registered in the database.
    
    Args:
        message: Incoming message
    """
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
    
    # Check if user is premium
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


@dp.message(F.text == "📝 Пост")
async def text_post_handler(message: types.Message, state: FSMContext):
    """Handle text-only post request"""
    await state.set_state(PostGeneration.waiting_for_topic)
    await state.update_data(post_type="text")
    rag_status = "с RAG" if rag_service.is_enabled() else "обычный"
    await message.answer(f"✍️ <b>Напиши тему поста</b> ({rag_status})!")


@dp.message(F.text == "🖼️ Пост с фото")
async def image_post_handler(message: types.Message, state: FSMContext):
    """Handle post with images request"""
    if not IMAGES_ENABLED:
        await message.answer("❌ <b>Генерация изображений недоступна</b>\nAPI ключ Pexels не настроен.")
        return
    
    await state.set_state(PostGeneration.waiting_for_topic)
    await state.update_data(post_type="images")
    rag_status = "с RAG" if rag_service.is_enabled() else "обычный"
    await message.answer(f"✍️ <b>Напиши тему поста с фото</b> ({rag_status})!")


@dp.message(F.text.in_({"❓ Помощь", "ℹ️ Статус", "📊 Статистика"}))
async def menu_handler(message: types.Message, state: FSMContext):
    """
    Handle menu button presses.
    
    Responds to help, status and statistics requests with appropriate information.
    
    Args:
        message: Incoming message
        state: FSM context
    """
    logger.debug(f"Menu handler: {message.text}")
    
    rag_status = "с RAG" if rag_service.is_enabled() else "обычный"
    
    if message.text == "❓ Помощь":
        await state.clear()  # Clear any active state
        await message.answer(
            f"🎯 <b>Как использовать:</b>\n"
            f"• 📝 <b>Пост</b> - только текст\n"
            f"• 🖼️ <b>Пост с фото</b> - текст + до 3 изображений\n"
            f"• Пиши тему, получи готовый контент!\n"
            f"• 🌐 Авто RU/EN перевод\n\n"
            f"<b>Команды:</b>\n"
            f"• /start - Начать работу\n"
            f"• /subscribe - Премиум подписка\n"
            f"• /status - Статус подписки\n\n"
            f"<code>Техподдержка: @твой_nick</code>"
        )
    elif message.text == "ℹ️ Статус":
        await state.clear()  # Clear any active state
        
        # Check premium status
        user_is_premium = await is_premium(message.from_user.id)
        premium_status = "🌟 Premium" if user_is_premium else "Free"
        
        await message.answer(
            f"✅ Bot: Online\n"
            f"✅ Perplexity: {config.api_model}\n"
            f"📚 RAG: {'ON' if rag_service.is_enabled() else 'OFF'}\n"
            f"🌐 Translate: {'ON' if translation_service.is_enabled() else 'OFF'}\n"
            f"🖼️ Images: {'ON' if IMAGES_ENABLED else 'OFF'}\n"
            f"💎 Status: {premium_status}\n"
            f"⏰ Автопост: каждые {config.autopost_interval_hours}ч → {config.channel_id}"
        )
    elif message.text == "📊 Статистика":
        await state.clear()  # Clear any active state
        # Admin-only feature
        if message.from_user.id not in ADMIN_USER_IDS:
            await message.answer("❌ <b>Доступ запрещён!</b> Эта функция только для администраторов.")
            return
        
        if not STATS_ENABLED:
            await message.answer("❌ <b>Статистика недоступна</b>\nМодуль статистики не установлен.")
            return
        
        # Get statistics
        stats = stats_tracker.get_stats()
        premium_count = await count_premium()
        
        await message.answer(
            f"📊 <b>Статистика бота</b>\n\n"
            f"👥 Всего пользователей: {stats['total_users']}\n"
            f"🌟 Премиум пользователей: {premium_count}\n"
            f"📝 Всего постов: {stats['total_generations']}\n"
            f"📅 Сегодня: {stats['today_generations']}\n"
            f"📈 Эта неделя: {stats['week_generations']}\n\n"
            f"🔝 <b>Топ пользователей:</b>\n" + 
            "\n".join([f"{i+1}. User {uid}: {count}" for i, (uid, count) in enumerate(stats['top_users'][:5])])
        )


@dp.message(Command("stats"))
async def stats_command(message: types.Message):
    """
    Handle /stats command for admins.
    
    Shows premium user statistics and other relevant metrics.
    
    Args:
        message: Incoming message
    """
    user_id = message.from_user.id
    
    # Admin-only feature
    if user_id not in ADMIN_USER_IDS:
        await message.answer("❌ <b>Доступ запрещён!</b> Эта функция только для администраторов.")
        return
    
    # Get premium count
    premium_count = await count_premium()
    
    stats_text = f"📊 <b>Администраторская статистика</b>\n\n"
    stats_text += f"🌟 Премиум пользователей: <b>{premium_count}</b>\n"
    
    if STATS_ENABLED and stats_tracker:
        stats = stats_tracker.get_stats()
        stats_text += f"👥 Всего пользователей: <b>{stats['total_users']}</b>\n"
        stats_text += f"📝 Всего постов: <b>{stats['total_generations']}</b>\n"
        stats_text += f"📅 Сегодня: <b>{stats['today_generations']}</b>\n"
        stats_text += f"📈 Эта неделя: <b>{stats['week_generations']}</b>\n"
    
    await message.answer(stats_text)


@dp.message(Command("generate"))
async def generate_command(message: types.Message):
    """
    Handle /generate command (premium only).
    
    This is a premium-only command for direct content generation.
    
    Args:
        message: Incoming message
    """
    user_id = message.from_user.id
    
    # Check if user is premium
    user_is_premium = await is_premium(user_id)
    
    if not user_is_premium:
        await message.answer(
            "🔒 <b>Premium Feature</b>\n\n"
            "The /generate command is only available for premium subscribers.\n\n"
            "Upgrade to premium to unlock this and other exclusive features!\n"
            "Use /subscribe to get started."
        )
        return
    
    # Extract topic from command
    command_parts = message.text.split(maxsplit=1)
    if len(command_parts) < 2:
        await message.answer(
            "ℹ️ <b>Использование:</b>\n"
            "/generate <тема>\n\n"
            "<b>Пример:</b> /generate фитнес и здоровье"
        )
        return
    
    topic = command_parts[1]
    await message.answer("⏳ Генерирую контент...")
    
    content = await generate_content(topic, user_id)
    await message.answer(f"<b>✨ Готовый пост:</b>\n\n{content}")


@dp.message(PostGeneration.waiting_for_topic)
async def process_topic(message: types.Message, state: FSMContext):
    """
    Process user's topic and generate content.
    
    Handles both text-only and image posts based on state data.
    
    Args:
        message: Incoming message with topic
        state: FSM context
    """
    topic = message.text
    user_id = message.from_user.id
    data = await state.get_data()
    post_type = data.get("post_type", "text")
    
    logger.info(f"User {user_id} requested {post_type} post: '{topic}'")
    
    # Generate content
    await message.answer("⏳ Генерирую контент...")
    content = await generate_content(topic, user_id)
    
    # Handle image posts
    if post_type == "images" and IMAGES_ENABLED and image_fetcher:
        try:
            # Fetch images
            image_urls, error_msg = await image_fetcher.search_images(topic, max_images=3)
            
            if image_urls:
                # Send as media group with caption
                try:
                    media = []
                    logger.info(f"Creating media group with {len(image_urls)} images for user {user_id}")
                    for i, url in enumerate(image_urls):
                        logger.debug(f"Adding image {i+1}/{len(image_urls)}: {url}")
                        if i == 0:
                            # Add caption to first image
                            media.append(InputMediaPhoto(media=url, caption=f"<b>✨ Готовый пост:</b>\n\n{content}"))
                        else:
                            media.append(InputMediaPhoto(media=url))
                    
                    await message.answer_media_group(media)
                    logger.info(f"Post with {len(image_urls)} images sent successfully to user {user_id}")
                except Exception as e:
                    logger.error(f"Error sending media group to user {user_id}: {e}", exc_info=True)
                    logger.error(f"Failed image URLs: {image_urls}")
                    # Fallback to text-only with recovery message
                    await message.answer(
                        f"<b>✨ Готовый пост:</b>\n\n{content}\n\n"
                        f"⚠️ Ошибка отправки изображений.\n"
                        f"💡 Попробуйте заново: нажмите 🖼️ <b>Пост с фото</b>"
                    )
            else:
                # No images found, send text only with error details and recovery message
                error_detail = f": {error_msg}" if error_msg else ""
                await message.answer(
                    f"<b>✨ Готовый пост:</b>\n\n{content}\n\n"
                    f"⚠️ Изображения не найдены{error_detail}\n"
                    f"💡 Попробуйте другую тему или позже: 🖼️ <b>Пост с фото</b>"
                )
                logger.warning(f"No images found for '{topic}' (user {user_id}): {error_msg}")
        except Exception as e:
            logger.error(f"Error fetching images for '{topic}' (user {user_id}): {e}", exc_info=True)
            await message.answer(
                f"<b>✨ Готовый пост:</b>\n\n{content}\n\n"
                f"⚠️ Ошибка поиска изображений: {str(e)}\n"
                f"💡 Попробуйте заново: 🖼️ <b>Пост с фото</b>"
            )
    else:
        # Text-only post
        await message.answer(f"<b>✨ Готовый пост:</b>\n\n{content}")
    
    # Clear state
    await state.clear()


# Autoposter configuration
AUTOPOST_TOPICS = [
    'SMM Москва',
    'фитнес',
    'питание',
    'мотивация',
    'бизнес'
]


async def auto_post():
    """
    Automated posting function.
    
    Selects a random topic from predefined list and posts generated
    content to the configured channel. Randomly decides whether to include images.
    """
    topic = random.choice(AUTOPOST_TOPICS)
    # Randomly decide if this autopost should include images (50% chance if enabled)
    include_images = IMAGES_ENABLED and random.choice([True, False])
    
    logger.info(f"🕒 Автопост: {topic} (with images: {include_images})")
    
    try:
        content = await generate_content(topic)
        post_prefix = f"<b>🤖 Автопост {random.randint(1,999)}:</b>\n\n"
        
        if include_images:
            # Try to fetch and send with images
            try:
                image_urls, error_msg = await image_fetcher.search_images(topic, max_images=3)
                
                if image_urls:
                    # Send as media group with caption
                    media = []
                    logger.info(f"Creating autopost media group with {len(image_urls)} images for topic '{topic}'")
                    for i, url in enumerate(image_urls):
                        logger.debug(f"Autopost image {i+1}/{len(image_urls)}: {url}")
                        if i == 0:
                            # Add caption to first image
                            media.append(InputMediaPhoto(media=url, caption=f"{post_prefix}{content}"))
                        else:
                            media.append(InputMediaPhoto(media=url))
                    
                    await bot.send_media_group(config.channel_id, media)
                    logger.info(f"✅ Автопост с {len(image_urls)} изображениями опубликован: {topic} → {config.channel_id}")
                    return
                else:
                    logger.warning(f"No images found for autopost '{topic}': {error_msg}. Falling back to text-only.")
            except Exception as e:
                logger.error(f"Error fetching/sending images for autopost '{topic}': {e}", exc_info=True)
                logger.error(f"Autopost fallback to text-only due to image error")
        
        # Send text-only (either by choice or fallback)
        await bot.send_message(
            config.channel_id,
            f"{post_prefix}{content}"
        )
        logger.info(f"✅ Автопост (текст) успешно опубликован: {topic} → {config.channel_id}")
    except Exception as e:
        logger.error(f"❌ Ошибка автопоста: {e}", exc_info=True)


async def on_startup():
    """
    Bot startup function.
    
    Initializes database and configures schedulers.
    """
    # Initialize database
    await init_db()
    logger.info("✅ Database initialized")
    
    # Image fetcher is ready (API keys loaded during initialization)
    if IMAGES_ENABLED and image_fetcher:
        logger.info("Image fetcher ready with Pexels/Pixabay APIs")
    
    scheduler = AsyncIOScheduler()
    
    # Setup autoposter
    scheduler.add_job(
        auto_post,
        'interval',
        hours=config.autopost_interval_hours
    )
    logger.info(
        f"🚀 Автопостинг запущен: каждые {config.autopost_interval_hours}ч → {config.channel_id}"
    )
    
    # Setup subscription expiration checker
    setup_expiration_job(scheduler, bot)
    
    scheduler.start()


async def main():
    """
    Main entry point.
    
    Starts the bot and begins polling for updates.
    """
    logger.info("=" * 60)
    logger.info("✅ BOT v3.0 WITH SUBSCRIPTIONS READY!")
    logger.info("=" * 60)
    
    await on_startup()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
