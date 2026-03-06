"""
AI Content Telegram Bot — canonical runtime entry point.

This bot generates AI-powered content for Telegram channels using Perplexity API.
Supports optional RAG (Retrieval-Augmented Generation), translation, image
generation, subscription/payment handling, and SaaS usage metering.

Run the bot:
    python bot.py

For Railway (or any production deploy), set the start command to ``python bot.py``
(or rely on the Procfile which already points here).

``main.py`` is a thin compatibility wrapper that delegates to this file.
"""

import asyncio
import random
import re
import sys
import time
from typing import Optional

from bs4 import BeautifulSoup
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart, Command
from aiogram.exceptions import TelegramBadRequest
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

# Import database and user management
from database.database import init_db, get_session
from database.models import UserRole, UserStatus
from services import user_service

# SaaS services
from services.tenant_service import resolve_user_and_tenant
from services.budget_service import check_tenant_budget, should_send_budget_warning, mark_budget_warned
from services.pricing_service import estimate_tokens_conservative, calculate_cost_usd
from services.usage_service import record_usage_event, record_blocked_usage_event

# Import utils for instance management
from utils import InstanceLock, is_another_instance_running, shutdown_manager, PollingManager

# Subscription / payment handlers
from handlers import subscription_router
from middlewares import SubscriptionMiddleware

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
    from services.image_fetcher import ImageFetcher

    # Initialize with both API keys
    image_fetcher = ImageFetcher(
        pexels_key=config.pexels_api_key,
        pixabay_key=config.pixabay_api_key,
    )
    # Images are enabled if at least one API key is configured
    IMAGES_ENABLED = bool(config.pexels_api_key or config.pixabay_api_key)
    if IMAGES_ENABLED:
        logger.info(
            f"✅ Image fetcher enabled (Pexels: {bool(config.pexels_api_key)}, Pixabay: {bool(config.pixabay_api_key)})"
        )
    else:
        logger.warning("⚠️ Image fetcher available but no API keys configured")
except ImportError:
    IMAGES_ENABLED = False
    image_fetcher = None
    logger.warning("⚠️ image_fetcher module not available")

# Get admin user IDs from config
ADMIN_USER_IDS = config.admin_user_ids

# Telegram caption length limit
TELEGRAM_CAPTION_MAX_LENGTH = 1024

# Log startup information (without sensitive data)
logger.info("=" * 60)
logger.info("AI Content Telegram Bot Starting...")
logger.info("=" * 60)

config_info = config.get_safe_config_info()
logger.info(f"Configuration loaded: {config_info}")
logger.info(f"RAG Status: {'ENABLED' if rag_service.is_enabled() else 'DISABLED'}")
logger.info(f"Translation Status: {'ENABLED' if translation_service.is_enabled() else 'DISABLED'}")
logger.info(f"🖼️ Pexels: {'ON' if config.pexels_api_key else 'OFF'}")
logger.info(f"Statistics Status: {'ENABLED' if STATS_ENABLED else 'DISABLED'}")
logger.info(f"Admin Users: {len(ADMIN_USER_IDS)}")


def _validate_bot_token(token: Optional[str]) -> str:
    """Validate BOT_TOKEN format and fail fast with a clear message if invalid."""
    if not token or not token.strip():
        logger.error("BOT_TOKEN is empty. Set the BOT_TOKEN environment variable.")
        raise SystemExit("Missing BOT_TOKEN")
    token = token.strip()
    if not re.match(r"^\d+:[A-Za-z0-9_-]+$", token):
        logger.error(
            "BOT_TOKEN format looks wrong. Ensure you pasted the BotFather token "
            "exactly (no quotes, no extra spaces, no 'Bot ' prefix)."
        )
        raise SystemExit("Invalid BOT_TOKEN format")
    return token


# Initialize bot and dispatcher
bot = Bot(
    token=_validate_bot_token(config.bot_token),
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
dp = Dispatcher(storage=MemoryStorage())

# Register subscription / payment router
dp.include_router(subscription_router)

# Register subscription middleware.
# premium_commands is empty by default so the middleware is a pass-through
# until specific commands are added to the premium gate.
dp.message.middleware(SubscriptionMiddleware(premium_commands=[]))

# Global scheduler instance
scheduler: Optional[AsyncIOScheduler] = None


# FSM States for post generation
class PostGeneration(StatesGroup):
    waiting_for_topic = State()
    post_type = State()  # "text" or "images"


# Main keyboard for all users
kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📝 Пост"), KeyboardButton(text="🖼️ Пост с фото")],
        [KeyboardButton(text="❓ Помощь"), KeyboardButton(text="ℹ️ Статус")],
    ],
    resize_keyboard=True,
)

# Admin keyboard with statistics button
kb_admin = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📝 Пост"), KeyboardButton(text="🖼️ Пост с фото")],
        [KeyboardButton(text="❓ Помощь"), KeyboardButton(text="ℹ️ Статус")],
        [KeyboardButton(text="📊 Статистика")],
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
    content = re.sub(r"\(\d+\)", "", content)

    # Remove citation numbers in brackets: [1], [12], etc.
    content = re.sub(r"\[\d+\]", "", content)

    # Remove markdown links [text](url) - keep text, remove URL
    content = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", content)

    # Remove standalone URLs
    content = re.sub(r"https?://[^\s]+", "", content)

    # Remove standalone brackets that might be left
    content = re.sub(r"\[\]", "", content)

    # Clean up excessive whitespace
    content = re.sub(r"\s+", " ", content)
    content = re.sub(r"\s+([.,!?])", r"\1", content)

    # Clean up multiple line breaks
    content = re.sub(r"\n\s*\n\s*\n+", "\n\n", content)

    return content.strip()


def safe_html(content: str) -> str:
    """
    Sanitize HTML content for safe Telegram display.

    Removes or unwraps unsupported HTML tags and attributes to prevent
    TelegramBadRequest errors from malformed tags like <1>, <2>, etc.

    Telegram supports only these HTML tags:
    <b>, <i>, <u>, <s>, <code>, <pre>, <a>, <strong>, <em>

    Args:
        content: Raw HTML content that may contain unsupported tags

    Returns:
        Sanitized HTML content safe for Telegram
    """

    # First, remove invalid tags like <1>, <2>, <123>, etc. before BeautifulSoup processing
    # This prevents them from being HTML-escaped
    content = re.sub(r"</?(\d+)[^>]*>", "", content)

    # Parse the content with BeautifulSoup
    soup = BeautifulSoup(content, "html.parser")

    # Allowed tags for Telegram HTML formatting
    allowed_tags = ["b", "i", "u", "s", "code", "pre", "a", "strong", "em"]

    # Remove or unwrap unsupported tags
    for tag in soup.find_all(True):
        if tag.name not in allowed_tags:
            # Unwrap the tag (keep content, remove tag)
            tag.unwrap()
        elif tag.name == "a":
            # For anchor tags, unwrap if no valid href attribute
            href = tag.get("href", "")
            if not href or href == "#":
                tag.unwrap()
            else:
                # Keep only href attribute for valid links
                tag.attrs = {"href": href}

    # Convert back to string
    cleaned = str(soup)

    # Remove any remaining HTML-like patterns that aren't valid tags
    # This catches remaining unsupported tags
    cleaned = re.sub(
        r"<(?![/]?(?:b|i|u|s|code|pre|a|strong|em)(?:\s|>))[^>]*>", "", cleaned
    )

    return cleaned


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
    rag_context, rag_info = await rag_service.get_context(topic)

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
            generated_content = f"{content}{rag_info}"
        else:
            generated_content = content

        logger.info("Content generation completed successfully")
        return generated_content

    except PerplexityAPIError as e:
        logger.error(f"Content generation failed: {e}")
        return "❌ Не удалось сгенерировать контент. Попробуйте позже."
    except Exception as e:
        logger.error(f"Unexpected error during content generation: {e}", exc_info=True)
        return "❌ Произошла ошибка. Пожалуйста, попробуйте снова."


@dp.message(CommandStart())
async def start_handler(message: types.Message):
    """
    Handle /start command.

    Registers new users, checks ban status, and sends welcome message.

    Also ensures a default tenant/workspace exists for this user.

    Args:
        message: Incoming message
    """

    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name

    logger.info(f"User {user_id} started the bot")

    # Register or get user
    await user_service.register_or_get_user(
        telegram_id=user_id, username=username, first_name=first_name, last_name=last_name
    )

    # Ensure tenant exists (best-effort)
    try:
        async with get_session() as session:
            await resolve_user_and_tenant(
                session,
                telegram_id=user_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
            )
    except Exception as e:
        logger.warning(f"Failed to ensure default tenant for user {user_id}: {e}")

    # Check if user is banned
    if await user_service.is_user_banned(user_id):
        await message.answer(
            "🚫 <b>Ваш аккаунт заблокирован.</b>\n\n" "Обратитесь к администратору для разблокировки."
        )
        return

    rag_status = "✅ RAG" if rag_service.is_enabled() else "⚠️ Без RAG"
    translate_status = "🌐 RU/EN" if translation_service.is_enabled() else ""
    images_status = "🖼️ Images" if IMAGES_ENABLED else ""

    await message.answer(
        f"<b>🚀 AI Content Bot v2.2 PROD {rag_status} {translate_status} {images_status}</b>\n\n"
        f"💬 <i>Тема поста → готовый текст 200-300 слов!</i>\n\n"
        f"📡 Автопостинг: <code>{config.channel_id}</code> (каждые {config.autopost_interval_hours}ч)\n"
        f"⚙️ max_tokens={config.max_tokens} | {config.api_model}\n\n"
        f"<b>Примеры:</b> SMM Москва | фитнес | завтрак",
        reply_markup=get_keyboard(message.from_user.id),
    )


@dp.message(Command("generate"))
async def generate_command(message: types.Message):
    """Handle /generate command."""

    logger.info(f"User {message.from_user.id} used /generate command")
    await message.answer("Тест изображений работает!")


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
    """Handle menu button presses."""

    logger.debug(f"Menu handler: {message.text}")

    if message.text == "❓ Помощь":
        await state.clear()
        await message.answer(
            "🎯 <b>Как использовать:</b>\n"
            "• 📝 <b>Пост</b> - только текст\n"
            "• 🖼️ <b>Пост с фото</b> - текст + до 3 изображений\n"
            "• Пиши тему, получи готовый контент!\n"
            "• 🌐 Авто RU/EN перевод\n\n"
            "<b>Команды:</b> /start\n"
            "<code>Техподдержка: @твой_nick</code>"
        )
    elif message.text == "ℹ️ Статус":
        await state.clear()
        await message.answer(
            f"✅ Bot: Online\n"
            f"✅ Perplexity: {config.api_model}\n"
            f"📚 RAG: {'ON' if rag_service.is_enabled() else 'OFF'}\n"
            f"🌐 Translate: {'ON' if translation_service.is_enabled() else 'OFF'}\n"
            f"🖼️ Images: {'ON' if IMAGES_ENABLED else 'OFF'}\n"
            f"⏰ Автопост: каждые {config.autopost_interval_hours}ч → {config.channel_id}"
        )
    elif message.text == "📊 Статистика":
        await state.clear()
        if message.from_user.id not in ADMIN_USER_IDS:
            await message.answer("❌ <b>Доступ запрещён!</b> Эта функция только для администраторов.")
            return

        if not STATS_ENABLED:
            await message.answer("❌ <b>Статистика недоступна</b>\nМодуль статистики не установлен.")
            return

        report = stats_tracker.get_report()
        await message.answer(report)


# ==================== Admin Commands ====================


@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    """Admin panel - show admin commands"""

    user_id = message.from_user.id
    if not await user_service.is_user_admin(user_id):
        await message.answer("🚫 <b>У вас нет прав администратора.</b>")
        return

    await message.answer(
        "<b>👑 Панель администратора</b>\n\n"
        "<b>Доступные команды:</b>\n"
        "/users - Список всех пользователей\n"
        "/ban &lt;user_id&gt; - Заблокировать пользователя\n"
        "/unban &lt;user_id&gt; - Разблокировать пользователя\n"
        "/setrole &lt;user_id&gt; &lt;role&gt; - Изменить роль (admin/user/guest)\n"
        "/logs [user_id] - Просмотр логов\n"
        "/userinfo &lt;user_id&gt; - Информация о пользователе"
    )


@dp.message(Command("users"))
async def list_users(message: types.Message):
    """List all users (admin only)"""

    user_id = message.from_user.id
    if not await user_service.is_user_admin(user_id):
        await message.answer("🚫 <b>У вас нет прав администратора.</b>")
        return

    users = await user_service.get_all_users(limit=30)

    if not users:
        await message.answer("📋 <b>Нет зарегистрированных пользователей</b>")
        return

    users_text = "<b>👥 Список пользователей:</b>\n\n"
    for user in users:
        role_emoji = (
            "👑"
            if user.role == UserRole.ADMIN
            else "👤"
            if user.role == UserRole.USER
            else "👻"
        )
        status_emoji = "✅" if user.status == UserStatus.ACTIVE else "🚫"
        name = user.first_name or user.username or f"ID: {user.telegram_id}"
        users_text += (
            f"{role_emoji} {status_emoji} <b>{user_service.sanitize_for_log(name)}</b>\n"
            f"   ID: <code>{user.telegram_id}</code> | Role: {user.role.value} | Status: {user.status.value}\n\n"
        )

    await message.answer(users_text)


@dp.message(Command("ban"))
async def ban_user_command(message: types.Message):
    """Ban a user (admin only)"""

    user_id = message.from_user.id
    if not await user_service.is_user_admin(user_id):
        await message.answer("🚫 <b>У вас нет прав администратора.</b>")
        return

    args = message.text.split()
    if len(args) < 2:
        await message.answer("❌ <b>Использование:</b> /ban &lt;user_id&gt;")
        return

    try:
        target_user_id = int(args[1])
    except ValueError:
        await message.answer("❌ <b>Некорректный ID пользователя</b>")
        return

    if target_user_id == user_id:
        await message.answer("❌ <b>Вы не можете заблокировать себя</b>")
        return

    success = await user_service.update_user_status(
        telegram_id=target_user_id, new_status=UserStatus.BANNED, admin_id=user_id
    )

    if success:
        await message.answer(f"✅ <b>Пользователь {target_user_id} заблокирован</b>")
    else:
        await message.answer(f"❌ <b>Не удалось заблокировать пользователя {target_user_id}</b>")


@dp.message(Command("unban"))
async def unban_user_command(message: types.Message):
    """Unban a user (admin only)"""

    user_id = message.from_user.id
    if not await user_service.is_user_admin(user_id):
        await message.answer("🚫 <b>У вас нет прав администратора.</b>")
        return

    args = message.text.split()
    if len(args) < 2:
        await message.answer("❌ <b>Использование:</b> /unban &lt;user_id&gt;")
        return

    try:
        target_user_id = int(args[1])
    except ValueError:
        await message.answer("❌ <b>Некорректный ID пользователя</b>")
        return

    success = await user_service.update_user_status(
        telegram_id=target_user_id, new_status=UserStatus.ACTIVE, admin_id=user_id
    )

    if success:
        await message.answer(f"✅ <b>Пользователь {target_user_id} разблокирован</b>")
    else:
        await message.answer(f"❌ <b>Не удалось разблокировать пользователя {target_user_id}</b>")


@dp.message(Command("setrole"))
async def set_role_command(message: types.Message):
    """Set user role (admin only)"""

    user_id = message.from_user.id
    if not await user_service.is_user_admin(user_id):
        await message.answer("🚫 <b>У вас нет прав администратора.</b>")
        return

    args = message.text.split()
    if len(args) < 3:
        await message.answer(
            "❌ <b>Использование:</b> /setrole &lt;user_id&gt; &lt;role&gt;\n<b>Роли:</b> admin, user, guest"
        )
        return

    try:
        target_user_id = int(args[1])
        role_str = args[2].upper()

        if role_str not in ["ADMIN", "USER", "GUEST"]:
            await message.answer("❌ <b>Некорректная роль.</b> Доступные: admin, user, guest")
            return

        new_role = UserRole[role_str]

        if target_user_id == user_id and new_role != UserRole.ADMIN:
            await message.answer("❌ <b>Вы не можете изменить свою роль администратора</b>")
            return
    except ValueError:
        await message.answer("❌ <b>Некорректный ID пользователя</b>")
        return

    success = await user_service.update_user_role(
        telegram_id=target_user_id, new_role=new_role, admin_id=user_id
    )

    if success:
        await message.answer(f"✅ <b>Роль пользователя {target_user_id} изменена на {new_role.value}</b>")
    else:
        await message.answer(f"❌ <b>Не удалось изменить роль пользователя {target_user_id}</b>")


@dp.message(Command("logs"))
async def view_logs_command(message: types.Message):
    """View logs (admin only)"""

    user_id = message.from_user.id
    if not await user_service.is_user_admin(user_id):
        await message.answer("🚫 <b>У вас нет прав администратора.</b>")
        return

    args = message.text.split()
    target_user_id = None
    if len(args) >= 2:
        try:
            target_user_id = int(args[1])
        except ValueError:
            await message.answer("❌ <b>Некорректный ID пользователя</b>")
            return

    logs = await user_service.get_logs(telegram_id=target_user_id, limit=15)

    if not logs:
        await message.answer("📋 <b>Логи отсутствуют</b>")
        return

    logs_text = (
        f"<b>📋 Логи</b>{f' для пользователя {target_user_id}' if target_user_id else ''}:\n\n"
    )
    for log in logs:
        timestamp = log.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        logs_text += (
            f"<b>{timestamp}</b>\n"
            f"   User: <code>{log.user_id}</code>\n"
            f"   Action: {log.action}\n\n"
        )

    await message.answer(logs_text)


@dp.message(Command("userinfo"))
async def user_info_command(message: types.Message):
    """Get user information (admin only)"""

    user_id = message.from_user.id
    if not await user_service.is_user_admin(user_id):
        await message.answer("🚫 <b>У вас нет прав администратора.</b>")
        return

    args = message.text.split()
    if len(args) < 2:
        await message.answer("❌ <b>Использование:</b> /userinfo &lt;user_id&gt;")
        return

    try:
        target_user_id = int(args[1])
    except ValueError:
        await message.answer("❌ <b>Некорректный ID пользователя</b>")
        return

    user = await user_service.get_user(target_user_id)

    if not user:
        await message.answer(f"❌ <b>Пользователь {target_user_id} не найден</b>")
        return

    name = user.first_name or user.username or "N/A"
    username = f"@{user.username}" if user.username else "N/A"
    created = user.created_at.strftime("%Y-%m-%d %H:%M:%S")
    updated = user.updated_at.strftime("%Y-%m-%d %H:%M:%S")

    user_info = (
        "<b>👤 Информация о пользователе</b>\n\n"
        f"<b>ID:</b> <code>{user.telegram_id}</code>\n"
        f"<b>Имя:</b> {user_service.sanitize_for_log(name)}\n"
        f"<b>Username:</b> {user_service.sanitize_for_log(username)}\n"
        f"<b>Роль:</b> {user.role.value}\n"
        f"<b>Статус:</b> {user.status.value}\n"
        f"<b>Premium:</b> {'✅ Да' if user.is_premium else '❌ Нет'}\n"
        f"<b>Зарегистрирован:</b> {created}\n"
        f"<b>Обновлён:</b> {updated}"
    )

    await message.answer(user_info)


# ==================== End Admin Commands ====================


@dp.message(PostGeneration.waiting_for_topic)
async def generate_post(message: types.Message, state: FSMContext):
    """Handle user text messages and generate content with optional photo integration."""

    topic = message.text.strip()
    telegram_user_id = message.from_user.id
    logger.info(f"User {telegram_user_id} requested post about: {topic}")

    data = await state.get_data()
    post_type = data.get("post_type", "text")

    safe_topic_display = user_service.sanitize_for_log(topic)

    rag_marker = " +RAG" if rag_service.is_enabled() else ""
    await message.answer(
        f"<b>🔄 Генерирую</b> пост про <i>{safe_topic_display}</i>{rag_marker}... ⏳10-20с"
    )

    # Resolve tenant and enforce budget guardrails
    tenant_id: Optional[int] = None
    user_db_id: Optional[int] = None

    try:
        async with get_session() as session:
            user_db_id, tenant_id = await resolve_user_and_tenant(
                session,
                telegram_id=telegram_user_id,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name,
            )

            budget = await check_tenant_budget(session, tenant_id)
            if not budget.allowed:
                await record_blocked_usage_event(
                    session,
                    tenant_id=tenant_id,
                    user_id=user_db_id,
                    provider="perplexity",
                    model=getattr(config, "api_model", None),
                    reason="budget_exceeded",
                )
                await message.answer(
                    "⛔ <b>Лимит бюджета исчерпан.</b>\n\n"
                    "Генерация остановлена, так как превышен месячный лимит для вашего workspace."
                )
                await state.clear()
                return

            if budget.should_warn and should_send_budget_warning(tenant_id):
                await message.answer(
                    "⚠️ <b>Предупреждение по бюджету.</b>\n\n"
                    "Вы приближаетесь к месячному лимиту workspace."
                )
                mark_budget_warned(tenant_id)

            # Keep session open for usage recording
            generation_start = time.perf_counter()

            rag_context, rag_info = await rag_service.get_context(topic)

            try:
                content, search_keyword = await api_client.generate_content_with_keyword(
                    topic, rag_context
                )
                latency_ms = int((time.perf_counter() - generation_start) * 1000)

                raw_content_for_tokens = content

                content = sanitize_content(content)
                logger.debug(
                    f"Content sanitized, length: {len(content)}, search keyword: '{search_keyword}'"
                )

                if translation_service.is_enabled():
                    translated, lang = await translation_service.detect_and_translate(content)
                    content = translation_service.add_language_marker(translated, lang)

                if rag_info:
                    content = f"{content}{rag_info}"

                safe_content = safe_html(content)
                logger.debug(f"HTML sanitized: {len(content)}→{len(safe_content)} chars")

                # Estimate tokens conservatively (MVP)
                tokens_in = estimate_tokens_conservative(topic + (rag_context or ""))
                tokens_out = estimate_tokens_conservative(raw_content_for_tokens)
                tokens_total = tokens_in + tokens_out
                cost_usd = calculate_cost_usd(tokens_total=tokens_total, model=getattr(config, "api_model", None))

                await record_usage_event(
                    session,
                    tenant_id=tenant_id,
                    user_id=user_db_id,
                    provider="perplexity",
                    model=getattr(config, "api_model", None),
                    status="success",
                    latency_ms=latency_ms,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    tokens_total=tokens_total,
                    cost_usd=cost_usd,
                )

                # Track statistics
                if STATS_ENABLED:
                    stats_tracker.record_post(telegram_user_id, topic, post_type)

                safe_topic = user_service.sanitize_for_log(topic)
                await user_service.add_log(
                    telegram_id=telegram_user_id,
                    action=f"Generated post: '{safe_topic}' (type: {post_type})",
                )

                # Image sending
                if IMAGES_ENABLED and image_fetcher:
                    await message.answer("🖼️ Ищу фото...")

                    try:
                        image_urls = await image_fetcher.fetch_images(search_keyword, num_images=1)
                        image_url = image_urls[0] if image_urls and len(image_urls) > 0 else ""

                        if image_url:
                            logger.info(
                                f"✅ Sending photo with caption for user {telegram_user_id}, keyword: '{search_keyword}'"
                            )
                            try:
                                await message.answer_photo(
                                    photo=image_url,
                                    caption=safe_content[:TELEGRAM_CAPTION_MAX_LENGTH],
                                    parse_mode="HTML",
                                )
                            except TelegramBadRequest as e:
                                logger.warning(
                                    f"HTML parse error in photo caption, falling back to plain text: {e}"
                                )
                                await message.answer_photo(
                                    photo=image_url, caption=safe_content[:TELEGRAM_CAPTION_MAX_LENGTH]
                                )
                        else:
                            logger.warning(
                                f"No photo found for keyword '{search_keyword}', fallback to text"
                            )
                            try:
                                await message.answer(
                                    f"<b>✨ Готовый пост:</b>\n\n{safe_content}",
                                    parse_mode="HTML",
                                )
                            except TelegramBadRequest as e:
                                logger.warning(
                                    f"HTML parse error, falling back to plain text: {e}"
                                )
                                await message.answer(f"✨ Готовый пост:\n\n{safe_content}")
                    except Exception as e:
                        logger.error(
                            f"Error fetching photo for '{search_keyword}' (user {telegram_user_id}): {e}",
                            exc_info=True,
                        )
                        try:
                            await message.answer(
                                f"<b>✨ Готовый пост:</b>\n\n{safe_content}",
                                parse_mode="HTML",
                            )
                        except TelegramBadRequest as e:
                            logger.warning(
                                f"HTML parse error, falling back to plain text: {e}"
                            )
                            await message.answer(f"✨ Готовый пост:\n\n{safe_content}")
                else:
                    try:
                        await message.answer(
                            f"<b>✨ Готовый пост:</b>\n\n{safe_content}", parse_mode="HTML"
                        )
                    except TelegramBadRequest as e:
                        logger.warning(f"HTML parse error, falling back to plain text: {e}")
                        await message.answer(f"✨ Готовый пост:\n\n{safe_content}")

            except PerplexityAPIError as e:
                latency_ms = int((time.perf_counter() - generation_start) * 1000)
                logger.error(f"Content generation failed: {e}")
                await record_usage_event(
                    session,
                    tenant_id=tenant_id,
                    user_id=user_db_id,
                    provider="perplexity",
                    model=getattr(config, "api_model", None),
                    status="failed",
                    latency_ms=latency_ms,
                    error_code="perplexity_api_error",
                    cost_usd=0,
                )
                await message.answer("❌ Не удалось сгенерировать контент. Попробуйте позже.")
            except Exception as e:
                latency_ms = int((time.perf_counter() - generation_start) * 1000)
                logger.error(f"Unexpected error during content generation: {e}", exc_info=True)
                await record_usage_event(
                    session,
                    tenant_id=tenant_id,
                    user_id=user_db_id,
                    provider="perplexity",
                    model=getattr(config, "api_model", None),
                    status="failed",
                    latency_ms=latency_ms,
                    error_code="unexpected_error",
                    cost_usd=0,
                )
                await message.answer("❌ Произошла ошибка. Пожалуйста, попробуйте снова.")

    except Exception as e:
        logger.error(f"SaaS tenant/budget wrapper failed: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка. Пожалуйста, попробуйте снова.")

    await state.clear()


# Autoposter configuration
AUTOPOST_TOPICS = ["SMM Москва", "фитнес", "питание", "мотивация", "бизнес"]


async def auto_post():
    """Automated posting function."""

    topic = random.choice(AUTOPOST_TOPICS)
    include_images = IMAGES_ENABLED and random.choice([True, False])

    logger.info(f"🕒 Автопост: {topic} (with images: {include_images})")

    try:
        content = await generate_content(topic)

        safe_content = safe_html(content)
        logger.debug(f"Autopost HTML sanitized: {len(content)}→{len(safe_content)} chars")

        post_prefix = f"<b>🤖 Автопост {random.randint(1,999)}:</b>\n\n"

        if include_images:
            try:
                image_urls, error_msg = await image_fetcher.search_images(topic, max_images=3)

                if image_urls:
                    media = []
                    logger.info(
                        f"Creating autopost media group with {len(image_urls)} images for topic '{topic}'"
                    )
                    for i, url in enumerate(image_urls):
                        logger.debug(f"Autopost image {i+1}/{len(image_urls)}: {url}")
                        if i == 0:
                            media.append(InputMediaPhoto(media=url, caption=f"{post_prefix}{safe_content}"))
                        else:
                            media.append(InputMediaPhoto(media=url))

                    try:
                        await bot.send_media_group(config.channel_id, media)
                        logger.info(
                            f"✅ Автопост с {len(image_urls)} изображениями опубликован: {topic} → {config.channel_id}"
                        )
                        return
                    except TelegramBadRequest as e:
                        logger.warning(
                            f"HTML parse error in autopost media caption, falling back to text-only: {e}"
                        )
                else:
                    logger.warning(
                        f"No images found for autopost '{topic}': {error_msg}. Falling back to text-only."
                    )
            except Exception as e:
                logger.error(
                    f"Error fetching/sending images for autopost '{topic}': {e}", exc_info=True
                )
                logger.error("Autopost fallback to text-only due to image error")

        try:
            await bot.send_message(config.channel_id, f"{post_prefix}{safe_content}")
            logger.info(f"✅ Автопост (текст) успешно опубликован: {topic} → {config.channel_id}")
        except TelegramBadRequest as e:
            logger.warning(f"HTML parse error in autopost, falling back to plain text: {e}")
            await bot.send_message(
                config.channel_id, f"🤖 Автопост {random.randint(1,999)}:\n\n{safe_content}"
            )
    except Exception as e:
        logger.error(f"❌ Ошибка автопоста: {e}", exc_info=True)


async def on_startup():
    """Bot startup function."""

    global scheduler

    try:
        await init_db()
        logger.info("✅ Database initialized successfully")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise

    if IMAGES_ENABLED and image_fetcher:
        logger.info("Image fetcher ready with Pexels/Pixabay APIs")

    scheduler = AsyncIOScheduler()
    scheduler.add_job(auto_post, "interval", hours=config.autopost_interval_hours)
    scheduler.start()
    logger.info(
        f"🚀 Автопостинг запущен: каждые {config.autopost_interval_hours}ч → {config.channel_id}"
    )

    # Single-glance health summary so Railway/production operators can confirm
    # every component is up without grepping through scattered log lines.
    logger.info("=" * 60)
    logger.info("🏥 Startup health summary:")
    logger.info("  Database     : ✅ initialized")
    logger.info(f"  Scheduler    : ✅ running  (every {config.autopost_interval_hours}h)")
    logger.info(f"  RAG          : {'✅ enabled' if rag_service.is_enabled() else '⚠️  disabled'}")
    logger.info(
        f"  Translation  : {'✅ enabled' if translation_service.is_enabled() else '⚠️  disabled'}"
    )
    logger.info(f"  Images       : {'✅ enabled' if IMAGES_ENABLED else '⚠️  disabled (no API keys)'}")
    logger.info("=" * 60)

    shutdown_manager.register_callback(on_shutdown)
    shutdown_manager.register_signals()


async def on_shutdown():
    """Bot shutdown function."""

    global scheduler

    logger.info("🛑 Shutting down bot resources...")

    if scheduler and scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("✅ Scheduler stopped")

    try:
        if hasattr(api_client, "close"):
            await api_client.close()
            logger.info("✅ API client closed")
    except Exception as e:
        logger.warning(f"⚠️ Error closing API client: {e}")

    try:
        if rag_service.is_enabled() and hasattr(rag_service, "stop_observer"):
            await rag_service.stop_observer()
            logger.info("✅ RAG observer stopped")
    except Exception as e:
        logger.warning(f"⚠️ Error stopping RAG observer: {e}")

    try:
        await bot.session.close()
        logger.info("✅ Bot session closed")
    except Exception as e:
        logger.warning(f"⚠️ Error closing bot session: {e}")

    logger.info("✅ Shutdown complete")


async def main():
    """Main entry point."""

    # Validate startup configuration early – logs clear warnings for absent
    # optional-but-important settings (e.g. DATABASE_URL) before anything else runs.
    config.validate_startup()

    if is_another_instance_running():
        logger.error("❌ Another bot instance is already running. Exiting.")
        sys.exit(1)

    instance_lock = InstanceLock()
    if not instance_lock.acquire():
        logger.error("❌ Failed to acquire instance lock. Exiting.")
        sys.exit(1)

    logger.info("=" * 60)
    logger.info("✅ BOT PRODUCTION READY!")
    logger.info("=" * 60)
    logger.info(f"🔑 PEXELS_API_KEY доступен: {bool(config.pexels_api_key)}")
    logger.info(f"🔑 PIXABAY_API_KEY доступен: {bool(config.pixabay_api_key)}")

    try:
        await on_startup()

        polling_manager = PollingManager(
            max_retries=5,
            initial_delay=5.0,
            max_delay=300.0,
            backoff_factor=2.0,
        )

        async def on_conflict():
            logger.warning("💡 Conflict detected. Ensure no other instances are running.")

        await polling_manager.start_polling_with_retry(
            dp, bot, on_conflict_callback=on_conflict
        )
    except KeyboardInterrupt:
        logger.info("⚠️ Received keyboard interrupt")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
    finally:
        await shutdown_manager.shutdown()
        instance_lock.release()


if __name__ == "__main__":
    asyncio.run(main())
