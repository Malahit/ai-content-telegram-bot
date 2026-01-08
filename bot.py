import asyncio
import logging
import os
import random
import requests
from dotenv import load_dotenv
from typing import Optional
from functools import wraps

# Database
from database import db

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
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
PPLX_API_KEY = os.getenv("PPLX_API_KEY", "PERPLEXITY_API_KEY")
CHANNEL_ID = os.getenv("CHANNEL_ID", "@content_ai_helper_bot")  # Из .env!
ADMIN_IDS = os.getenv("ADMIN_IDS", "").split(",")  # Comma-separated admin IDs
ADMIN_IDS = [int(aid.strip()) for aid in ADMIN_IDS if aid.strip().isdigit()]

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

# === ACCESS CONTROL ===
async def check_user_access(user_id: int, required_role: Optional[str] = None) -> tuple[bool, Optional[dict]]:
    """
    Check if user has access to the bot.
    Returns (has_access, user_data)
    """
    user = await db.get_user(user_id)
    
    # User not registered
    if not user:
        return False, None
    
    # User is banned
    if user['status'] == 'banned':
        return False, user
    
    # Check role if required
    if required_role:
        role_hierarchy = {'guest': 0, 'user': 1, 'admin': 2}
        user_level = role_hierarchy.get(user['role'], 0)
        required_level = role_hierarchy.get(required_role, 0)
        
        if user_level < required_level:
            return False, user
    
    return True, user

async def ensure_user_registered(message: types.Message) -> bool:
    """Auto-register user if not in database."""
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    
    if not user:
        # Auto-register with guest role
        name = message.from_user.full_name or f"User_{user_id}"
        # Check if this is an admin from env
        role = 'admin' if user_id in ADMIN_IDS else 'guest'
        await db.register_user(user_id, name, role)
        logger.info(f"Auto-registered user {user_id} ({name}) as {role}")
        return True
    return False

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
    await ensure_user_registered(message)
    user = await db.get_user(message.from_user.id)
    
    rag_status = "✅ RAG" if RAG_ENABLED else "⚠️ Без RAG"
    translate_status = "🌐 RU/EN" if TRANSLATE_ENABLED else ""
    
    role_info = f"\n👤 Роль: <b>{user['role']}</b>" if user else ""
    
    await message.answer(
        f"<b>🚀 AI Content Bot v2.1 PROD {rag_status} {translate_status}</b>\n\n"
        f"💬 <i>Тема поста → готовый текст 200-300 слов!</i>\n\n"
        f"📡 Автопостинг: <code>{CHANNEL_ID}</code> (каждые 6ч)\n"
        f"⚙️ max_tokens=800 | sonar-small-online{role_info}\n\n"
        f"<b>Примеры:</b> SMM Москва | фитнес | завтрак\n\n"
        f"<b>Команды:</b> /register /help",
        reply_markup=kb
    )

@dp.message(Command("register"))
async def register_handler(message: types.Message):
    """Register or update user in the database."""
    user_id = message.from_user.id
    name = message.from_user.full_name or f"User_{user_id}"
    
    existing_user = await db.get_user(user_id)
    
    if existing_user:
        await message.answer(
            f"✅ Вы уже зарегистрированы!\n\n"
            f"👤 <b>ID:</b> <code>{user_id}</code>\n"
            f"📝 <b>Имя:</b> {existing_user['name']}\n"
            f"🎭 <b>Роль:</b> {existing_user['role']}\n"
            f"📊 <b>Статус:</b> {existing_user['status']}\n"
            f"📅 <b>Дата регистрации:</b> {existing_user['created_at']}"
        )
    else:
        # Determine role (admin from env or guest)
        role = 'admin' if user_id in ADMIN_IDS else 'guest'
        success = await db.register_user(user_id, name, role)
        
        if success:
            await message.answer(
                f"🎉 <b>Регистрация успешна!</b>\n\n"
                f"👤 <b>ID:</b> <code>{user_id}</code>\n"
                f"📝 <b>Имя:</b> {name}\n"
                f"🎭 <b>Роль:</b> {role}\n"
                f"📊 <b>Статус:</b> active\n\n"
                f"Используйте /help для списка доступных команд."
            )
            logger.info(f"User registered via /register: {user_id} ({name}) as {role}")
        else:
            await message.answer("❌ Ошибка при регистрации. Попробуйте позже.")

@dp.message(Command("help"))
async def help_handler(message: types.Message):
    """Show help with available commands based on user role."""
    await ensure_user_registered(message)
    user = await db.get_user(message.from_user.id)
    
    if not user or user['status'] == 'banned':
        await message.answer("❌ У вас нет доступа к боту. Обратитесь к администратору.")
        return
    
    base_help = (
        "🎯 <b>Доступные команды:</b>\n\n"
        "• /start - Главное меню\n"
        "• /register - Зарегистрироваться\n"
        "• /help - Эта справка\n"
        "• Отправьте тему для генерации поста\n"
    )
    
    if user['role'] in ['user', 'admin']:
        base_help += "\n📝 <b>Генерация контента доступна!</b>"
    
    if user['role'] == 'admin':
        base_help += (
            "\n\n👑 <b>Команды администратора:</b>\n"
            "• /list_users - Список пользователей\n"
            "• /ban <user_id> - Заблокировать пользователя\n"
            "• /unban <user_id> - Разблокировать пользователя\n"
            "• /set_role <user_id> <role> - Изменить роль\n"
            "  (роли: admin, user, guest)"
        )
    
    await message.answer(base_help)

@dp.message(Command("list_users"))
async def list_users_handler(message: types.Message):
    """List all users (admin only)."""
    await ensure_user_registered(message)
    has_access, user = await check_user_access(message.from_user.id, 'admin')
    
    if not has_access:
        await message.answer("❌ Недостаточно прав. Команда доступна только администраторам.")
        logger.warning(f"Unauthorized /list_users attempt by {message.from_user.id}")
        return
    
    users = await db.list_users()
    
    if not users:
        await message.answer("📋 Нет зарегистрированных пользователей.")
        return
    
    user_list = "👥 <b>Список пользователей:</b>\n\n"
    for u in users:
        status_emoji = "✅" if u['status'] == 'active' else "🚫"
        role_emoji = "👑" if u['role'] == 'admin' else "👤" if u['role'] == 'user' else "👻"
        user_list += (
            f"{status_emoji} {role_emoji} <b>{u['name']}</b>\n"
            f"   ID: <code>{u['id']}</code> | {u['role']} | {u['status']}\n\n"
        )
    
    await message.answer(user_list)
    logger.info(f"Admin {message.from_user.id} listed {len(users)} users")

@dp.message(Command("ban"))
async def ban_user_handler(message: types.Message):
    """Ban a user (admin only)."""
    await ensure_user_registered(message)
    has_access, user = await check_user_access(message.from_user.id, 'admin')
    
    if not has_access:
        await message.answer("❌ Недостаточно прав. Команда доступна только администраторам.")
        return
    
    # Parse user_id from command
    args = message.text.split()
    if len(args) < 2:
        await message.answer("⚠️ Использование: /ban <user_id>")
        return
    
    try:
        target_user_id = int(args[1])
    except ValueError:
        await message.answer("❌ Неверный формат user_id. Используйте число.")
        return
    
    # Prevent self-ban
    if target_user_id == message.from_user.id:
        await message.answer("❌ Вы не можете заблокировать самого себя!")
        return
    
    target_user = await db.get_user(target_user_id)
    if not target_user:
        await message.answer(f"❌ Пользователь с ID {target_user_id} не найден.")
        return
    
    success = await db.ban_user(target_user_id)
    if success:
        await message.answer(
            f"🚫 <b>Пользователь заблокирован</b>\n\n"
            f"ID: <code>{target_user_id}</code>\n"
            f"Имя: {target_user['name']}"
        )
        logger.info(f"Admin {message.from_user.id} banned user {target_user_id}")
    else:
        await message.answer("❌ Ошибка при блокировке пользователя.")

@dp.message(Command("unban"))
async def unban_user_handler(message: types.Message):
    """Unban a user (admin only)."""
    await ensure_user_registered(message)
    has_access, user = await check_user_access(message.from_user.id, 'admin')
    
    if not has_access:
        await message.answer("❌ Недостаточно прав. Команда доступна только администраторам.")
        return
    
    args = message.text.split()
    if len(args) < 2:
        await message.answer("⚠️ Использование: /unban <user_id>")
        return
    
    try:
        target_user_id = int(args[1])
    except ValueError:
        await message.answer("❌ Неверный формат user_id. Используйте число.")
        return
    
    target_user = await db.get_user(target_user_id)
    if not target_user:
        await message.answer(f"❌ Пользователь с ID {target_user_id} не найден.")
        return
    
    success = await db.unban_user(target_user_id)
    if success:
        await message.answer(
            f"✅ <b>Пользователь разблокирован</b>\n\n"
            f"ID: <code>{target_user_id}</code>\n"
            f"Имя: {target_user['name']}"
        )
        logger.info(f"Admin {message.from_user.id} unbanned user {target_user_id}")
    else:
        await message.answer("❌ Ошибка при разблокировке пользователя.")

@dp.message(Command("set_role"))
async def set_role_handler(message: types.Message):
    """Set user role (admin only)."""
    await ensure_user_registered(message)
    has_access, user = await check_user_access(message.from_user.id, 'admin')
    
    if not has_access:
        await message.answer("❌ Недостаточно прав. Команда доступна только администраторам.")
        return
    
    args = message.text.split()
    if len(args) < 3:
        await message.answer("⚠️ Использование: /set_role <user_id> <role>\n\nДоступные роли: admin, user, guest")
        return
    
    try:
        target_user_id = int(args[1])
        new_role = args[2].lower()
    except ValueError:
        await message.answer("❌ Неверный формат. Используйте: /set_role <user_id> <role>")
        return
    
    if new_role not in ['admin', 'user', 'guest']:
        await message.answer("❌ Неверная роль. Доступные: admin, user, guest")
        return
    
    target_user = await db.get_user(target_user_id)
    if not target_user:
        await message.answer(f"❌ Пользователь с ID {target_user_id} не найден.")
        return
    
    success = await db.update_user_role(target_user_id, new_role)
    if success:
        await message.answer(
            f"✅ <b>Роль изменена</b>\n\n"
            f"ID: <code>{target_user_id}</code>\n"
            f"Имя: {target_user['name']}\n"
            f"Новая роль: <b>{new_role}</b>"
        )
        logger.info(f"Admin {message.from_user.id} changed role of {target_user_id} to {new_role}")
    else:
        await message.answer("❌ Ошибка при изменении роли.")


@dp.message(F.text.in_({"📝 Пост", "❓ Помощь", "ℹ️ Статус"}))
async def menu_handler(message: types.Message):
    await ensure_user_registered(message)
    user = await db.get_user(message.from_user.id)
    
    if not user or user['status'] == 'banned':
        await message.answer("❌ У вас нет доступа к боту.")
        return
    
    rag_status = "с RAG" if RAG_ENABLED else "обычный"
    if message.text == "❓ Помощь":
        await help_handler(message)
    elif message.text == "ℹ️ Статус":
        await message.answer(
            f"✅ Bot: Online\n"
            f"✅ Perplexity: sonar-small-online\n"
            f"📚 RAG: {'ON' if RAG_ENABLED else 'OFF'}\n"
            f"🌐 Translate: {'ON' if TRANSLATE_ENABLED else 'OFF'}\n"
            f"⏰ Автопост: каждые 6ч → {CHANNEL_ID}\n\n"
            f"👤 Ваша роль: <b>{user['role']}</b>\n"
            f"📊 Статус: {user['status']}"
        )
    else:
        if user['role'] in ['user', 'admin']:
            await message.answer(f"✍️ <b>Напиши тему поста</b> ({rag_status})!")
        else:
            await message.answer(
                f"⚠️ Генерация постов доступна только для пользователей с ролью 'user' или 'admin'.\n"
                f"Ваша текущая роль: {user['role']}\n\n"
                f"Обратитесь к администратору для повышения прав."
            )

@dp.message(F.text, ~F.text.in_({"📝 Пост", "❓ Помощь", "ℹ️ Статус"}))
async def generate_post(message: types.Message):
    await ensure_user_registered(message)
    
    # Check access
    has_access, user = await check_user_access(message.from_user.id, 'user')
    
    if not has_access:
        if user and user['status'] == 'banned':
            await message.answer("🚫 <b>Вы заблокированы</b>\n\nОбратитесь к администратору.")
            logger.warning(f"Banned user {message.from_user.id} tried to generate post")
        elif user and user['role'] == 'guest':
            await message.answer(
                f"⚠️ Генерация постов доступна только для пользователей с ролью 'user' или 'admin'.\n"
                f"Ваша текущая роль: {user['role']}\n\n"
                f"Обратитесь к администратору: /help"
            )
        else:
            await message.answer("❌ Сначала зарегистрируйтесь: /register")
        return
    
    topic = message.text.strip()
    await message.answer(f"<b>🔄 Генерирую</b> пост про <i>{topic}</i>{' +RAG' if RAG_ENABLED else ''}... ⏳10-20с")
    
    content = await generate_content(topic)
    await message.answer(f"<b>✨ Готовый пост:</b>\n\n{content}")
    logger.info(f"User {message.from_user.id} ({user['name']}) generated post: {topic}")

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
    await db.init_db()
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
