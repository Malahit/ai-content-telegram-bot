"""
AI Content Telegram Bot - Main module.

This bot generates AI-powered content for Telegram channels using Perplexity API.
Supports optional RAG (Retrieval-Augmented Generation), translation, and image generation features.
"""

import asyncio
import random
import re
import time
from typing import Optional

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
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
from handlers.content import generate_perplexity_image_with_fallback
from database import image_db

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


def get_inline_keyboard(topic: str) -> InlineKeyboardMarkup:
    """
    Create inline keyboard with action buttons for posts.
    
    Args:
        topic: The topic used for the post
        
    Returns:
        InlineKeyboardMarkup with buttons for regeneration
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔄 Новый пост", callback_data=f"new_post:{topic}"),
            InlineKeyboardButton(text="🎨 Новое фото", callback_data=f"regen_image:{topic}")
        ]
    ])
    return keyboard


async def generate_perplexity_image(topic: str) -> Optional[str]:
    """
    Generate an image using Perplexity API with caching and Pexels fallback.
    
    This is a wrapper around the handlers.content module for backward compatibility.
    
    Args:
        topic: The topic/prompt for image generation
        
    Returns:
        Image URL or None if generation failed
    """
    # Use the handler module with image_fetcher for fallback support
    return await generate_perplexity_image_with_fallback(topic, image_fetcher if IMAGES_ENABLED else None)



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
    images_status = "🎨 AI Images"  # Always available via Perplexity
    
    await message.answer(
        f"<b>🚀 AI Content Bot v2.3 PROD {rag_status} {translate_status} {images_status}</b>\n\n"
        f"💬 <i>Тема поста → готовый текст 200-300 слов + AI-изображение!</i>\n\n"
        f"🎨 <b>Perplexity AI Images</b> - реалистичные изображения\n"
        f"📡 Автопостинг: <code>{config.channel_id}</code> (каждые {config.autopost_interval_hours}ч)\n"
        f"⚙️ max_tokens={config.max_tokens} | {config.api_model}\n\n"
        f"<b>Примеры:</b> фитнес | завтрак | SMM Москва",
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
    """Handle post with images request - uses Perplexity AI image generation"""
    await state.set_state(PostGeneration.waiting_for_topic)
    await state.update_data(post_type="images")
    rag_status = "с RAG" if rag_service.is_enabled() else "обычный"
    await message.answer(f"✍️ <b>Напиши тему поста с AI-фото</b> ({rag_status})!")


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
            f"• 🖼️ <b>Пост с фото</b> - текст + AI-изображение (Perplexity)\n"
            f"• Пиши тему, получи готовый контент!\n"
            f"• 🌐 Авто RU/EN перевод\n"
            f"• 🎨 AI-изображения от Perplexity\n\n"
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
            f"🎨 AI Images: ON (Perplexity)\n"
            f"🖼️ Fallback: {'ON' if IMAGES_ENABLED else 'OFF'} (Pexels/Pixabay)\n"
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
    Uses Perplexity for image generation with Pexels fallback.
    
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
    
    if post_type == "images":
        # Generate/fetch image using Perplexity with Pexels fallback
        await message.answer("🎨 Генерирую AI-изображение с Perplexity...")
        try:
            image_url = await generate_perplexity_image(topic)
            
            if image_url:
                # Send text with AI-generated image
                try:
                    logger.info(f"Sending AI-generated image to user {user_id}: {image_url}")
                    await message.answer_photo(
                        photo=image_url,
                        caption=f"<b>✨ Готовый пост:</b>\n\n{content}",
                        reply_markup=get_inline_keyboard(topic)
                    )
                    logger.info(f"Post with AI image sent successfully to user {user_id}")
                except Exception as e:
                    logger.error(f"Error sending photo to user {user_id}: {e}", exc_info=True)
                    logger.error(f"Failed image URL: {image_url}")
                    # Fallback to text-only with recovery message
                    await message.answer(
                        f"<b>✨ Готовый пост:</b>\n\n{content}\n\n"
                        f"⚠️ Ошибка отправки изображения.\n"
                        f"💡 Попробуйте заново: нажмите 🖼️ <b>Пост с фото</b>",
                        reply_markup=get_inline_keyboard(topic)
                    )
            else:
                # No image generated, send text only with error details
                await message.answer(
                    f"<b>✨ Готовый пост:</b>\n\n{content}\n\n"
                    f"⚠️ Не удалось сгенерировать изображение (Perplexity и Pexels недоступны)\n"
                    f"💡 Попробуйте позже или другую тему",
                    reply_markup=get_inline_keyboard(topic)
                )
                logger.warning(f"No image generated for '{topic}' (user {user_id})")
        except Exception as e:
            logger.error(f"Error generating image for '{topic}' (user {user_id}): {e}", exc_info=True)
            await message.answer(
                f"<b>✨ Готовый пост:</b>\n\n{content}\n\n"
                f"⚠️ Ошибка генерации изображения: {str(e)}\n"
                f"💡 Попробуйте заново: 🖼️ <b>Пост с фото</b>",
                reply_markup=get_inline_keyboard(topic)
            )
    else:
        # Text-only post
        await message.answer(
            f"<b>✨ Готовый пост:</b>\n\n{content}",
            reply_markup=get_inline_keyboard(topic)
        )
    
    # Clear state
    await state.clear()


@dp.callback_query(F.data.startswith("new_post:"))
async def callback_new_post(callback: types.CallbackQuery):
    """
    Handle 'New post' button callback.
    
    Generates a completely new post (text + image) for the same topic.
    
    Args:
        callback: Callback query from inline button
    """
    topic = callback.data.split(":", 1)[1]
    user_id = callback.from_user.id
    logger.info(f"User {user_id} requested new post for topic: {topic}")
    
    await callback.answer("🔄 Генерирую новый пост...")
    await callback.message.answer(f"<b>🔄 Генерирую новый пост</b> про <i>{topic}</i>... ⏳")
    
    # Generate new content
    content = await generate_content(topic)
    
    # Generate new image
    image_url = await generate_perplexity_image(topic)
    
    if image_url:
        try:
            await callback.message.answer_photo(
                photo=image_url,
                caption=f"<b>✨ Новый пост:</b>\n\n{content}",
                reply_markup=get_inline_keyboard(topic)
            )
            logger.info(f"New post with image sent to user {user_id}")
        except Exception as e:
            logger.error(f"Error sending new post photo to user {user_id}: {e}", exc_info=True)
            await callback.message.answer(
                f"<b>✨ Новый пост:</b>\n\n{content}\n\n"
                f"⚠️ Ошибка отправки изображения",
                reply_markup=get_inline_keyboard(topic)
            )
    else:
        await callback.message.answer(
            f"<b>✨ Новый пост:</b>\n\n{content}\n\n"
            f"⚠️ Не удалось сгенерировать изображение",
            reply_markup=get_inline_keyboard(topic)
        )


@dp.callback_query(F.data.startswith("regen_image:"))
async def callback_regenerate_image(callback: types.CallbackQuery):
    """
    Handle 'Regenerate image only' button callback.
    
    Generates only a new image while keeping the same text.
    
    Args:
        callback: Callback query from inline button
    """
    topic = callback.data.split(":", 1)[1]
    user_id = callback.from_user.id
    logger.info(f"User {user_id} requested image regeneration for topic: {topic}")
    
    await callback.answer("🎨 Генерирую новое изображение...")
    
    # Get the current message text (caption)
    current_text = callback.message.caption or callback.message.text
    
    # Extract just the content part (remove the header)
    if current_text:
        # Remove the "✨ Готовый пост:" or "✨ Новый пост:" header and any error messages
        content = current_text.split("\n\n", 1)[1] if "\n\n" in current_text else current_text
        # Remove any warning/error messages at the end
        if "⚠️" in content:
            content = content.split("⚠️")[0].strip()
    else:
        # Fallback: regenerate content if we can't extract it
        content = await generate_content(topic)
    
    # Generate new image (note: may use cache if same topic requested recently)
    image_url = await generate_perplexity_image(topic)
    
    if image_url:
        try:
            await callback.message.answer_photo(
                photo=image_url,
                caption=f"<b>✨ Готовый пост (новое фото):</b>\n\n{content}",
                reply_markup=get_inline_keyboard(topic)
            )
            logger.info(f"New image sent to user {user_id}")
        except Exception as e:
            logger.error(f"Error sending regenerated image to user {user_id}: {e}", exc_info=True)
            await callback.message.answer(
                f"⚠️ Ошибка отправки нового изображения. Попробуйте еще раз."
            )
    else:
        await callback.message.answer(
            f"⚠️ Не удалось сгенерировать новое изображение. Попробуйте позже."
        )


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
    content to the configured channel. Uses Perplexity for images with Pexels fallback.
    """
    topic = random.choice(AUTOPOST_TOPICS)
    # Randomly decide if this autopost should include images (50% chance)
    include_images = random.choice([True, False])
    
    logger.info(f"🕒 Автопост: {topic} (with images: {include_images})")
    
    try:
        content = await generate_content(topic)
        post_prefix = f"<b>🤖 Автопост {random.randint(1,999)}:</b>\n\n"
        
        if include_images:
            # Try to generate image with Perplexity
            try:
                image_url = await generate_perplexity_image(topic)
                
                if image_url:
                    # Send with AI-generated image
                    logger.info(f"Sending autopost with AI image for topic '{topic}'")
                    await bot.send_photo(
                        config.channel_id,
                        photo=image_url,
                        caption=f"{post_prefix}{content}"
                    )
                    logger.info(f"✅ Автопост с AI-изображением опубликован: {topic} → {config.channel_id}")
                    return
                else:
                    logger.warning(f"No image generated for autopost '{topic}'. Falling back to text-only.")
            except Exception as e:
                logger.error(f"Error generating/sending image for autopost '{topic}': {e}", exc_info=True)
                logger.error(f"Autopost fallback to text-only due to image error")
        
        # Send text-only (either by choice or fallback)
        await bot.send_message(
            config.channel_id,
            f"{post_prefix}{content}"
        )
        logger.info(f"✅ Автопост (текст) успешно опубликован: {topic} → {config.channel_id}")
    except Exception as e:
        logger.error(f"❌ Ошибка автопоста: {e}", exc_info=True)


async def cleanup_image_cache():
    """Periodic cleanup of expired image cache entries."""
    deleted_count = image_db.cleanup_expired()
    if deleted_count > 0:
        logger.info(f"🧹 Cleaned up {deleted_count} expired image cache entries")


async def on_startup():
    """
    Bot startup function.
    
    Configures and starts the autoposter and cache cleanup schedulers.
    """
    # Image fetcher is ready (API keys loaded during initialization)
    if IMAGES_ENABLED and image_fetcher:
        logger.info("Image fetcher ready with Pexels/Pixabay APIs")
    
    scheduler = AsyncIOScheduler()
    
    # Add autopost job
    scheduler.add_job(
        auto_post,
        'interval',
        hours=config.autopost_interval_hours
    )
    
    # Add cache cleanup job (run daily)
    scheduler.add_job(
        cleanup_image_cache,
        'interval',
        hours=24
    )
    
    scheduler.start()
    logger.info(
        f"🚀 Автопостинг запущен: каждые {config.autopost_interval_hours}ч → {config.channel_id}"
    )
    logger.info("🧹 Image cache cleanup scheduled: every 24 hours")


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
