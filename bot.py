import asyncio
import logging
import os
import random
import requests
from dotenv import load_dotenv
from typing import Optional
from functools import wraps

# 🌐 Опционально: перевод (если нужно)
try:
    from langdetect import detect
    from deep_translator import GoogleTranslator
    TRANSLATE_ENABLED = True
    translator = GoogleTranslator(source='auto', target='ru')
except ImportError:
    TRANSLATE_ENABLED = False
    print("⚠️ deep_translator недоступен")

# 🔥 RAG (опционально)
try:
    from rag import create_vectorstore
    vectorstore = create_vectorstore()
    RAG_ENABLED = True
    print("✅ RAG активирован!")
except ImportError:
    RAG_ENABLED = False
    vectorstore = None
    print("⚠️ RAG недоступен")

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart, Command
from aiogram import Bot, Dispatcher, F, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# User management database
import database

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
PPLX_API_KEY = os.getenv("PPLX_API_KEY", "PERPLEXITY_API_KEY")
CHANNEL_ID = os.getenv("CHANNEL_ID", "@content_ai_helper_bot")  # Из .env!

if not BOT_TOKEN:
    raise RuntimeError("❌ BOT_TOKEN не найден в .env!")
if not PPLX_API_KEY:
    raise RuntimeError("❌ PPLX_API_KEY не найден в .env!")

print(f"🚀 BOT_TOKEN: ✅ | PPLX_API_KEY: ✅ | CHANNEL_ID: {CHANNEL_ID}")
print(f"✅ RAG: {'ON' if RAG_ENABLED else 'OFF'} | 🌐 Translate: {'ON' if TRANSLATE_ENABLED else 'OFF'}")

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📝 Пост"), KeyboardButton(text="❓ Помощь"), KeyboardButton(text="ℹ️ Статус")]
    ],
    resize_keyboard=True,
)

async def detect_lang_and_translate(text: str) -> tuple[str, str]:
    """🌐 RU/EN авто перевод"""
    if not TRANSLATE_ENABLED:
        return text, 'ru'
    try:
        detected = detect(text)
        if detected == 'en':
            translated = translator.translate(text)
            return translated, detected
        return text, detected
    except:
        return text, 'ru'

async def generate_content(topic: str, max_tokens: int = 800) -> str:
    """🎯 Perplexity API (работает!)"""
    print(f"🔥 Генерируем: {topic}")
    
    # 🔥 RAG контекст
    rag_context = ""
    rag_info = ""
    if RAG_ENABLED and vectorstore:
        relevant_docs = vectorstore.similarity_search(topic, k=2)
        rag_context = "\n".join([doc.page_content[:400] for doc in relevant_docs])
        rag_info = f"\n📚 {len(relevant_docs)} файлов"
        print(f"✅ RAG: {len(relevant_docs)} docs")
    
    headers = {
        "Authorization": f"Bearer {PPLX_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "sonar",  # ✅ Сегодняшний фикс!
        "messages": [
            {"role": "system", "content": "SMM-копирайтер Telegram. 200-300 слов, эмодзи, структура, CTA."},
            {"role": "user", "content": f"{rag_context}\n\nПост про: {topic}"}
        ],
        "max_tokens": max_tokens,
        "temperature": 0.8,
        "stream": False
    }
    
    try:
        resp = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers=headers, json=data, timeout=45
        )
        print(f"📡 API: {resp.status_code}")
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"].strip()
        
        # 🌐 Перевод
        if TRANSLATE_ENABLED:
            translated, lang = await detect_lang_and_translate(content)
            content = f"{translated}\n\n🌐 [{lang.upper()}]"
        
        return f"{content}{rag_info}"
    except Exception as e:
        logger.error(f"API Error: {e}")
        return f"❌ API недоступен: {str(e)[:100]}"

@dp.message(CommandStart())
async def start_handler(message: types.Message):
    rag_status = "✅ RAG" if RAG_ENABLED else "⚠️ Без RAG"
    translate_status = "🌐 RU/EN" if TRANSLATE_ENABLED else ""
    await message.answer(
        f"<b>🚀 AI Content Bot v2.1 PROD {rag_status} {translate_status}</b>\n\n"
        f"💬 <i>Тема поста → готовый текст 200-300 слов!</i>\n\n"
        f"📡 Автопостинг: <code>{CHANNEL_ID}</code> (каждые 6ч)\n"
        f"⚙️ max_tokens=800 | sonar-small-online\n\n"
        f"<b>Примеры:</b> SMM Москва | фитнес | завтрак\n\n"
        f"<b>Команды управления:</b>\n"
        f"/register - Регистрация пользователя\n"
        f"/set_role - Установить роль (только админ)\n"
        f"/list_users - Список пользователей (только админ)",
        reply_markup=kb
    )


# ==================== USER MANAGEMENT COMMANDS ====================

def admin_only(func):
    """Decorator to restrict commands to admin users only."""
    @wraps(func)
    async def wrapper(message: types.Message, *args, **kwargs):
        if not database.is_user_admin(message.from_user.id):
            await message.answer("❌ <b>Access Denied</b>\n\nThis command is only available to administrators.")
            return
        return await func(message, *args, **kwargs)
    return wrapper


@dp.message(Command("register"))
async def register_handler(message: types.Message):
    """Handle user registration."""
    user_id = message.from_user.id
    username = message.from_user.username
    
    # Get full name from command or use Telegram name
    args = message.text.split(maxsplit=1)
    if len(args) > 1:
        full_name = args[1].strip()
    else:
        full_name = message.from_user.full_name or "Unknown User"
    
    # Validate full name
    if not full_name or len(full_name) < 2:
        await message.answer(
            "❌ <b>Invalid Name</b>\n\n"
            "Usage: <code>/register Your Full Name</code>\n"
            "Example: <code>/register John Smith</code>"
        )
        return
    
    if len(full_name) > 100:
        await message.answer("❌ Name is too long. Maximum 100 characters allowed.")
        return
    
    # Register user
    success = database.register_user(user_id, username, full_name)
    
    if success:
        await message.answer(
            f"✅ <b>Registration Successful!</b>\n\n"
            f"👤 Name: <b>{full_name}</b>\n"
            f"🆔 ID: <code>{user_id}</code>\n"
            f"👔 Role: <b>user</b>\n\n"
            f"You can now use all bot features!"
        )
        logger.info(f"New user registered: {user_id} - {full_name}")
    else:
        user = database.get_user(user_id)
        if user:
            await message.answer(
                f"⚠️ <b>Already Registered</b>\n\n"
                f"👤 Name: <b>{user['full_name']}</b>\n"
                f"👔 Role: <b>{user['role']}</b>\n"
                f"📅 Registered: {user['registered_at'][:10]}"
            )
        else:
            await message.answer("❌ Registration failed. Please try again later.")


@dp.message(Command("set_role"))
@admin_only
async def set_role_handler(message: types.Message):
    """Handle role assignment (admin only)."""
    args = message.text.split()
    
    # Validate command format
    if len(args) != 3:
        await message.answer(
            "❌ <b>Invalid Format</b>\n\n"
            "Usage: <code>/set_role USER_ID ROLE</code>\n\n"
            "Available roles: admin, user, guest\n"
            "Example: <code>/set_role 123456789 admin</code>"
        )
        return
    
    try:
        target_user_id = int(args[1])
    except ValueError:
        await message.answer("❌ Invalid user ID. Must be a number.")
        return
    
    new_role = args[2].lower()
    
    # Set role
    success, msg = database.set_user_role(target_user_id, new_role, message.from_user.id)
    await message.answer(msg)


@dp.message(Command("list_users"))
@admin_only
async def list_users_handler(message: types.Message):
    """Handle user listing with pagination (admin only)."""
    # Parse page number from command
    args = message.text.split()
    page = 1
    
    if len(args) > 1:
        try:
            page = int(args[1])
            if page < 1:
                page = 1
        except ValueError:
            await message.answer("❌ Invalid page number.")
            return
    
    # Get users
    users, total_users, total_pages = database.list_users(page=page, per_page=10)
    
    if not users:
        await message.answer("📋 <b>No users found</b>")
        return
    
    # Format user list
    response = f"👥 <b>Users List</b> (Page {page}/{total_pages})\n"
    response += f"📊 Total: {total_users} users\n\n"
    
    for user in users:
        status_icon = "🚫" if user['is_banned'] else "✅"
        role_icon = {"admin": "👑", "user": "👤", "guest": "👁"}.get(user['role'], "❓")
        username_str = f"@{user['username']}" if user['username'] else "—"
        
        response += (
            f"{status_icon} {role_icon} <b>{user['full_name']}</b>\n"
            f"   ID: <code>{user['user_id']}</code> | {username_str}\n"
            f"   Role: <i>{user['role']}</i> | Registered: {user['registered_at'][:10]}\n\n"
        )
    
    # Add pagination info
    if total_pages > 1:
        response += f"\n💡 Use <code>/list_users {page + 1}</code> for next page"
    
    await message.answer(response)


@dp.message(Command("ban"))
@admin_only
async def ban_handler(message: types.Message):
    """Handle user ban (admin only)."""
    args = message.text.split()
    
    if len(args) != 2:
        await message.answer(
            "❌ <b>Invalid Format</b>\n\n"
            "Usage: <code>/ban USER_ID</code>\n"
            "Example: <code>/ban 123456789</code>"
        )
        return
    
    try:
        target_user_id = int(args[1])
    except ValueError:
        await message.answer("❌ Invalid user ID. Must be a number.")
        return
    
    success, msg = database.ban_user(target_user_id, message.from_user.id)
    await message.answer(msg)


@dp.message(Command("unban"))
@admin_only
async def unban_handler(message: types.Message):
    """Handle user unban (admin only)."""
    args = message.text.split()
    
    if len(args) != 2:
        await message.answer(
            "❌ <b>Invalid Format</b>\n\n"
            "Usage: <code>/unban USER_ID</code>\n"
            "Example: <code>/unban 123456789</code>"
        )
        return
    
    try:
        target_user_id = int(args[1])
    except ValueError:
        await message.answer("❌ Invalid user ID. Must be a number.")
        return
    
    success, msg = database.unban_user(target_user_id, message.from_user.id)
    await message.answer(msg)


# ==================== END USER MANAGEMENT COMMANDS ====================

@dp.message(F.text.in_({"📝 Пост", "❓ Помощь", "ℹ️ Статус"}))
async def menu_handler(message: types.Message):
    rag_status = "с RAG" if RAG_ENABLED else "обычный"
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
            f"✅ Perplexity: sonar-small-online\n"
            f"📚 RAG: {'ON' if RAG_ENABLED else 'OFF'}\n"
            f"🌐 Translate: {'ON' if TRANSLATE_ENABLED else 'OFF'}\n"
            f"⏰ Автопост: каждые 6ч → {CHANNEL_ID}"
        )
    else:
        await message.answer(f"✍️ <b>Напиши тему поста</b> ({rag_status})!")

@dp.message(F.text, ~F.text.in_({"📝 Пост", "❓ Помощь", "ℹ️ Статус"}))
async def generate_post(message: types.Message):
    topic = message.text.strip()
    await message.answer(f"<b>🔄 Генерирую</b> пост про <i>{topic}</i>{' +RAG' if RAG_ENABLED else ''}... ⏳10-20с")
    
    content = await generate_content(topic)
    await message.answer(f"<b>✨ Готовый пост:</b>\n\n{content}")

# 🕒 АВТОПОСТИНГ (восстановлен!)
async def auto_post():
    topics = ['SMM Москва', 'фитнес', 'питание', 'мотивация', 'бизнес']
    topic = random.choice(topics)
    print(f"🕒 Автопост #{random.randint(1,999)}: {topic}")
    try:
        content = await generate_content(topic)
        await bot.send_message(CHANNEL_ID, f"<b>🤖 Автопост {random.randint(1,999)}:</b>\n\n{content}")
        logger.info(f"✅ Автопост: {topic} → {CHANNEL_ID}")
    except Exception as e:
        logger.error(f"❌ Автопост failed: {e}")

async def on_startup():
    # Initialize database
    database.init_database()
    logger.info("✅ Database initialized")
    
    # Start scheduler
    scheduler = AsyncIOScheduler()
    scheduler.add_job(auto_post, 'interval', hours=6)
    scheduler.start()
    logger.info(f"🚀 Автопостинг запущен: каждые 6ч → {CHANNEL_ID}")

async def main():
    logger.info("✅ BOT v2.1 PRODUCTION READY!")
    await on_startup()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
