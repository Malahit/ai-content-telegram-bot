"""
AI Content Telegram Bot - Main module.

This bot generates AI-powered content for Telegram channels using Perplexity API.
Supports optional RAG (Retrieval-Augmented Generation), translation, and image generation features.
"""

import asyncio
import random
import re
from typing import Optional

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
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
    from image_fetcher import image_fetcher
    IMAGES_ENABLED = bool(config.pexels_api_key)
    logger.info(f"✅ Image fetcher {'enabled' if IMAGES_ENABLED else 'available but no API key'}")
except ImportError:
    IMAGES_ENABLED = False
    image_fetcher = None
    logger.warning("⚠️ image_fetcher module not available")

# Get admin user IDs from config
ADMIN_USER_IDS = config.admin_user_ids

# Log startup information (without sensitive data)
logger.info("=" * 60)
logger.info("AI Content Telegram Bot v2.2 Starting...")
logger.info("=" * 60)

config_info = config.get_safe_config_info()
logger.info(f"Configuration loaded: {config_info}")
logger.info(f"RAG Status: {'ENABLED' if rag_service.is_enabled() else 'DISABLED'}")
logger.info(f"Translation Status: {'ENABLED' if translation_service.is_enabled() else 'DISABLED'}")
logger.info(f"Images Status: {'ENABLED' if IMAGES_ENABLED else 'DISABLED'}")
logger.info(f"Statistics Status: {'ENABLED' if STATS_ENABLED else 'DISABLED'}")
logger.info(f"Admin Users: {len(ADMIN_USER_IDS)}")


# Initialize bot and dispatcher
bot = Bot(
    token=config.bot_token,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher(storage=MemoryStorage())

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
    """Get appropriate keyboard based on user role"""
    if user_id in ADMIN_USER_IDS:
        return kb_admin
    return kb


def sanitize_content(content: str) -> str:
    """
    Clean generated content by removing citation artifacts and URLs.
    
    Removes:
    - Citation numbers in parentheses like (1), (123)
    - Citation numbers in brackets like [1], [12]
    - Markdown links [text](url) - keeps text, removes URL
    - Standalone URLs
    - Excessive whitespace from removals
    
    Args:
        content: Raw content from API
        
    Returns:
        Cleaned content without citations and URLs
    """
    # Remove citation numbers in parentheses: (1), (123), etc.
    content = re.sub(r'\(\d+\)', '', content)
    
    # Remove citation numbers in brackets: [1], [12], etc.
    content = re.sub(r'\[\d+\]', '', content)
    
    # Remove markdown links [text](url) - keep text, remove URL
    content = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', content)
    
    # Remove standalone URLs
    content = re.sub(r'https?://[^\s]+', '', content)
    
    # Remove standalone brackets that might be left
    content = re.sub(r'\[\]', '', content)
    
    # Clean up excessive whitespace
    content = re.sub(r'\s+', ' ', content)
    content = re.sub(r'\s+([.,!?])', r'\1', content)
    
    # Clean up multiple line breaks
    content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)
    
    return content.strip()


async def generate_content(topic: str, max_tokens: Optional[int] = None) -> str:
    """
    Generate content for a given topic using Perplexity API.
    
    This function orchestrates content generation by:
    1. Retrieving RAG context if available
    2. Calling the API to generate content
    3. Applying translation if needed
    4. Adding metadata about RAG sources
    
    Args:
        topic: The topic to generate content about
        max_tokens: Maximum tokens for the response (optional)
        
    Returns:
        str: Generated content with optional translation and metadata
    """
    logger.info(f"Starting content generation for topic: {topic}")
    
    # Get RAG context if available
    rag_context, rag_info = rag_service.get_context(topic)
    
    try:
        # Generate content using API
        content = api_client.generate_content(topic, rag_context, max_tokens)
        
        # Sanitize content to remove citation artifacts and URLs
        content = sanitize_content(content)
        logger.debug(f"Content sanitized, length: {len(content)}")
        
        # Apply translation if enabled
        if translation_service.is_enabled():
            translated, lang = await translation_service.detect_and_translate(content)
            content = translation_service.add_language_marker(translated, lang)
        
        # Add RAG info if available (only if there is RAG info to add)
        if rag_info:
            final_content = f"{content}{rag_info}"
        else:
            final_content = content
        
        logger.info("Content generation completed successfully")
        return final_content
        
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
    
    Args:
        message: Incoming message
    """
    logger.info(f"User {message.from_user.id} started the bot")
    
    rag_status = "✅ RAG" if rag_service.is_enabled() else "⚠️ Без RAG"
    translate_status = "🌐 RU/EN" if translation_service.is_enabled() else ""
    images_status = "🖼️ Images" if IMAGES_ENABLED else ""
    
    await message.answer(
        f"<b>🚀 AI Content Bot v2.2 PROD {rag_status} {translate_status} {images_status}</b>\n\n"
        f"💬 <i>Тема поста → готовый текст 200-300 слов!</i>\n\n"
        f"📡 Автопостинг: <code>{config.channel_id}</code> (каждые {config.autopost_interval_hours}ч)\n"
        f"⚙️ max_tokens={config.max_tokens} | {config.api_model}\n\n"
        f"<b>Примеры:</b> SMM Москва | фитнес | завтрак",
        reply_markup=get_keyboard(message.from_user.id)
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
            f"<b>Команды:</b> /start\n"
            f"<code>Техподдержка: @твой_nick</code>"
        )
    elif message.text == "ℹ️ Статус":
        await state.clear()  # Clear any active state
        await message.answer(
            f"✅ Bot: Online\n"
            f"✅ Perplexity: {config.api_model}\n"
            f"📚 RAG: {'ON' if rag_service.is_enabled() else 'OFF'}\n"
            f"🌐 Translate: {'ON' if translation_service.is_enabled() else 'OFF'}\n"
            f"🖼️ Images: {'ON' if IMAGES_ENABLED else 'OFF'}\n"
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
        
        report = stats_tracker.get_report()
        await message.answer(report)


@dp.message(PostGeneration.waiting_for_topic)
async def generate_post(message: types.Message, state: FSMContext):
    """
    Handle user text messages and generate content.
    
    Takes user's topic and generates a post using AI with optional RAG context.
    Can generate text-only or posts with images based on FSM state.
    
    Args:
        message: Incoming message with topic
        state: FSM context
    """
    topic = message.text.strip()
    user_id = message.from_user.id
    logger.info(f"User {user_id} requested post about: {topic}")
    
    # Get the post type from state
    data = await state.get_data()
    post_type = data.get("post_type", "text")
    
    rag_marker = ' +RAG' if rag_service.is_enabled() else ''
    await message.answer(
        f"<b>🔄 Генерирую</b> пост про <i>{topic}</i>{rag_marker}... ⏳10-20с"
    )
    
    # Generate content
    content = await generate_content(topic)
    
    # Track statistics
    if STATS_ENABLED:
        stats_tracker.record_post(user_id, topic, post_type)
    
    if post_type == "images" and IMAGES_ENABLED:
        # Fetch images for the post
        await message.answer("🖼️ Ищу подходящие изображения...")
        try:
            # Use async search_images
            image_urls = await image_fetcher.search_images(topic, max_images=3)
            
            if image_urls:
                # Send text with images
                try:
                    # Create media group
                    media = []
                    for i, url in enumerate(image_urls):
                        if i == 0:
                            # Add caption to first image
                            media.append(InputMediaPhoto(media=url, caption=f"<b>✨ Готовый пост:</b>\n\n{content}"))
                        else:
                            media.append(InputMediaPhoto(media=url))
                    
                    await message.answer_media_group(media)
                    logger.info(f"Post with {len(image_urls)} images sent to user {user_id}")
                except Exception as e:
                    logger.error(f"Error sending images: {e}")
                    # Fallback to text-only
                    await message.answer(f"<b>✨ Готовый пост:</b>\n\n{content}\n\n⚠️ Ошибка загрузки изображений")
            else:
                # No images found, send text only
                await message.answer(f"<b>✨ Готовый пост:</b>\n\n{content}\n\n⚠️ Изображения не найдены")
        except Exception as e:
            logger.error(f"Error fetching images: {e}")
            await message.answer(f"<b>✨ Готовый пост:</b>\n\n{content}\n\n⚠️ Ошибка поиска изображений")
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
    content to the configured channel.
    """
    topic = random.choice(AUTOPOST_TOPICS)
    logger.info(f"🕒 Автопост: {topic}")
    
    try:
        content = await generate_content(topic)
        await bot.send_message(
            config.channel_id,
            f"<b>🤖 Автопост {random.randint(1,999)}:</b>\n\n{content}"
        )
        logger.info(f"✅ Автопост успешно опубликован: {topic} → {config.channel_id}")
    except Exception as e:
        logger.error(f"❌ Ошибка автопоста: {e}", exc_info=True)


async def on_startup():
    """
    Bot startup function.
    
    Configures and starts the autoposter scheduler.
    """
    # Validate image API key if configured
    if IMAGES_ENABLED and image_fetcher:
        logger.info("Validating image API key...")
        try:
            image_fetcher.validate_api_key()
        except RuntimeError as e:
            logger.error(f"Image API key validation error: {e}")
            # Don't raise - allow bot to start without images
    
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        auto_post,
        'interval',
        hours=config.autopost_interval_hours
    )
    scheduler.start()
    logger.info(
        f"🚀 Автопостинг запущен: каждые {config.autopost_interval_hours}ч → {config.channel_id}"
    )


async def main():
    """
    Main entry point.
    
    Starts the bot and begins polling for updates.
    """
    logger.info("=" * 60)
    logger.info("✅ BOT v2.2 PRODUCTION READY!")
    logger.info("=" * 60)
    
    await on_startup()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
