"""
AI Content Telegram Bot - Main module.

This bot generates AI-powered content for Telegram channels using Perplexity API.
Supports optional RAG (Retrieval-Augmented Generation) and translation features.
"""

import asyncio
import random
from typing import Optional

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Import custom modules
from config import config
from logger_config import logger
from api_client import api_client, PerplexityAPIError
from translation_service import translation_service
from rag_service import rag_service

# Log startup information (without sensitive data)
logger.info("=" * 60)
logger.info("AI Content Telegram Bot v2.2 Starting...")
logger.info("=" * 60)

config_info = config.get_safe_config_info()
logger.info(f"Configuration loaded: {config_info}")
logger.info(f"RAG Status: {'ENABLED' if rag_service.is_enabled() else 'DISABLED'}")
logger.info(f"Translation Status: {'ENABLED' if translation_service.is_enabled() else 'DISABLED'}")


# Initialize bot and dispatcher
bot = Bot(
    token=config.bot_token,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher(storage=MemoryStorage())

# Create keyboard markup
kb = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="📝 Пост"),
            KeyboardButton(text="❓ Помощь"),
            KeyboardButton(text="ℹ️ Статус")
        ]
    ],
    resize_keyboard=True,
)


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
        
        # Apply translation if enabled
        if translation_service.is_enabled():
            translated, lang = await translation_service.detect_and_translate(content)
            content = translation_service.add_language_marker(translated, lang)
        
        # Add RAG info if available
        final_content = f"{content}{rag_info}"
        
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
    
    await message.answer(
        f"<b>🚀 AI Content Bot v2.2 PROD {rag_status} {translate_status}</b>\n\n"
        f"💬 <i>Тема поста → готовый текст 200-300 слов!</i>\n\n"
        f"📡 Автопостинг: <code>{config.channel_id}</code> (каждые {config.autopost_interval_hours}ч)\n"
        f"⚙️ max_tokens={config.max_tokens} | {config.api_model}\n\n"
        f"<b>Примеры:</b> SMM Москва | фитнес | завтрак",
        reply_markup=kb
    )


@dp.message(F.text.in_({"📝 Пост", "❓ Помощь", "ℹ️ Статус"}))
async def menu_handler(message: types.Message):
    """
    Handle menu button presses.
    
    Responds to help and status requests with appropriate information.
    
    Args:
        message: Incoming message
    """
    logger.debug(f"Menu handler: {message.text}")
    
    rag_status = "с RAG" if rag_service.is_enabled() else "обычный"
    
    if message.text == "❓ Помощь":
        await message.answer(
            f"🎯 <b>Как использовать:</b>\n"
            f"• Пиши тему поста\n"
            f"• Получи 250 слов {rag_status} + эмодзи\n"
            f"• 🌐 Авто RU/EN перевод\n\n"
            f"<b>Команды:</b> /start\n"
            f"<code>Техподдержка: @твой_nick</code>"
        )
    elif message.text == "ℹ️ Статус":
        await message.answer(
            f"✅ Bot: Online\n"
            f"✅ Perplexity: {config.api_model}\n"
            f"📚 RAG: {'ON' if rag_service.is_enabled() else 'OFF'}\n"
            f"🌐 Translate: {'ON' if translation_service.is_enabled() else 'OFF'}\n"
            f"⏰ Автопост: каждые {config.autopost_interval_hours}ч → {config.channel_id}"
        )
    else:
        await message.answer(f"✍️ <b>Напиши тему поста</b> ({rag_status})!")


@dp.message(F.text, ~F.text.in_({"📝 Пост", "❓ Помощь", "ℹ️ Статус"}))
async def generate_post(message: types.Message):
    """
    Handle user text messages and generate content.
    
    Takes user's topic and generates a post using AI with optional RAG context.
    
    Args:
        message: Incoming message with topic
    """
    topic = message.text.strip()
    logger.info(f"User {message.from_user.id} requested post about: {topic}")
    
    rag_marker = ' +RAG' if rag_service.is_enabled() else ''
    await message.answer(
        f"<b>🔄 Генерирую</b> пост про <i>{topic}</i>{rag_marker}... ⏳10-20с"
    )
    
    content = await generate_content(topic)
    await message.answer(f"<b>✨ Готовый пост:</b>\n\n{content}")


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
    post_id = random.randint(1, 999)
    
    logger.info(f"Starting autopost #{post_id} for topic: {topic}")
    
    try:
        content = await generate_content(topic)
        
        await bot.send_message(
            config.channel_id,
            f"<b>🤖 Автопост #{post_id}:</b>\n\n{content}"
        )
        
        logger.info(f"Autopost #{post_id} published successfully to {config.channel_id}")
        
    except Exception as e:
        logger.error(f"Autopost #{post_id} failed: {e}", exc_info=True)


async def on_startup():
    """
    Initialize scheduler and start autoposting.
    
    Sets up APScheduler to run auto_post function at configured intervals.
    """
    logger.info("Initializing scheduler for autoposting")
    
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        auto_post,
        'interval',
        hours=config.autopost_interval_hours
    )
    scheduler.start()
    
    logger.info(
        f"Autoposting started: every {config.autopost_interval_hours}h → {config.channel_id}"
    )


async def main():
    """
    Main entry point for the bot.
    
    Initializes all components and starts polling for messages.
    """
    logger.info("=" * 60)
    logger.info("BOT v2.2 PRODUCTION READY!")
    logger.info("=" * 60)
    
    await on_startup()
    
    logger.info("Starting polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        raise
