import asyncio
import logging
import os
import random
import requests
from dotenv import load_dotenv
from typing import Optional

# Database and user management
from database import db
from user_manager import user_manager, sanitize_for_log

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
    # Register or update user in database
    user_id = message.from_user.id
    user_name = message.from_user.full_name or message.from_user.username or f"User{user_id}"
    
    # Check if user exists
    existing_user = await db.get_user(user_id)
    if not existing_user:
        # Register new user
        await user_manager.register_user(user_id, user_name, role='user')
    
    # Check if user is banned
    if await user_manager.is_user_banned(user_id):
        await message.answer("🚫 <b>Ваш аккаунт заблокирован.</b>\n\nОбратитесь к администратору.")
        return
    
    rag_status = "✅ RAG" if RAG_ENABLED else "⚠️ Без RAG"
    translate_status = "🌐 RU/EN" if TRANSLATE_ENABLED else ""
    await message.answer(
        f"<b>🚀 AI Content Bot v2.1 PROD {rag_status} {translate_status}</b>\n\n"
        f"💬 <i>Тема поста → готовый текст 200-300 слов!</i>\n\n"
        f"📡 Автопостинг: <code>{CHANNEL_ID}</code> (каждые 6ч)\n"
        f"⚙️ max_tokens=800 | sonar-small-online\n\n"
        f"<b>Примеры:</b> SMM Москва | фитнес | завтрак",
        reply_markup=kb
    )

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
    # Check if user is banned
    user_id = message.from_user.id
    if await user_manager.is_user_banned(user_id):
        await message.answer("🚫 <b>Ваш аккаунт заблокирован.</b>")
        return
    
    topic = message.text.strip()
    await message.answer(f"<b>🔄 Генерирую</b> пост про <i>{topic}</i>{' +RAG' if RAG_ENABLED else ''}... ⏳10-20с")
    
    content = await generate_content(topic)
    await message.answer(f"<b>✨ Готовый пост:</b>\n\n{content}")
    
    # Log the action with sanitized topic
    safe_topic = sanitize_for_log(topic)
    await db.add_log(user_id, f"Generated post: '{safe_topic}'")

# Admin commands for user management
@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    """Admin panel - show admin commands"""
    user_id = message.from_user.id
    if not await user_manager.is_user_admin(user_id):
        await message.answer("🚫 <b>У вас нет прав администратора.</b>")
        return
    
    await message.answer(
        "<b>👨‍💼 Панель администратора</b>\n\n"
        "<b>Команды:</b>\n"
        "• /users - список пользователей\n"
        "• /ban &lt;user_id&gt; - заблокировать пользователя\n"
        "• /unban &lt;user_id&gt; - разблокировать пользователя\n"
        "• /setrole &lt;user_id&gt; &lt;role&gt; - изменить роль (admin/user/guest)\n"
        "• /logs [user_id] - просмотр логов\n"
        "• /userinfo &lt;user_id&gt; - информация о пользователе"
    )

@dp.message(Command("users"))
async def list_users(message: types.Message):
    """List all users (admin only)"""
    user_id = message.from_user.id
    if not await user_manager.is_user_admin(user_id):
        await message.answer("🚫 <b>У вас нет прав администратора.</b>")
        return
    
    users = await db.get_all_users()
    if not users:
        await message.answer("📋 <b>Пользователи не найдены.</b>")
        return
    
    response = "<b>👥 Список пользователей:</b>\n\n"
    for user in users:
        status_emoji = "🚫" if user.status == "banned" else "✅"
        role_emoji = "👨‍💼" if user.role == "admin" else "👤"
        response += f"{status_emoji} {role_emoji} <b>{user.name}</b>\n"
        response += f"  ID: <code>{user.id}</code>\n"
        response += f"  Роль: {user.role} | Статус: {user.status}\n"
        response += f"  Создан: {user.created_at.strftime('%Y-%m-%d %H:%M')}\n\n"
    
    await message.answer(response)

@dp.message(Command("ban"))
async def ban_user_command(message: types.Message):
    """Ban a user (admin only)"""
    user_id = message.from_user.id
    if not await user_manager.is_user_admin(user_id):
        await message.answer("🚫 <b>У вас нет прав администратора.</b>")
        return
    
    args = message.text.split()
    if len(args) != 2:
        await message.answer("❌ Использование: /ban &lt;user_id&gt;")
        return
    
    try:
        target_user_id = int(args[1])
    except ValueError:
        await message.answer("❌ Неверный ID пользователя")
        return
    
    if target_user_id == user_id:
        await message.answer("❌ Вы не можете заблокировать себя!")
        return
    
    success = await user_manager.ban_user(target_user_id, admin_id=user_id)
    if success:
        await message.answer(f"✅ Пользователь <code>{target_user_id}</code> заблокирован.")
    else:
        await message.answer(f"❌ Ошибка при блокировке пользователя <code>{target_user_id}</code>")

@dp.message(Command("unban"))
async def unban_user_command(message: types.Message):
    """Unban a user (admin only)"""
    user_id = message.from_user.id
    if not await user_manager.is_user_admin(user_id):
        await message.answer("🚫 <b>У вас нет прав администратора.</b>")
        return
    
    args = message.text.split()
    if len(args) != 2:
        await message.answer("❌ Использование: /unban &lt;user_id&gt;")
        return
    
    try:
        target_user_id = int(args[1])
    except ValueError:
        await message.answer("❌ Неверный ID пользователя")
        return
    
    success = await user_manager.unban_user(target_user_id, admin_id=user_id)
    if success:
        await message.answer(f"✅ Пользователь <code>{target_user_id}</code> разблокирован.")
    else:
        await message.answer(f"❌ Ошибка при разблокировке пользователя <code>{target_user_id}</code>")

@dp.message(Command("setrole"))
async def set_role_command(message: types.Message):
    """Set user role (admin only)"""
    user_id = message.from_user.id
    if not await user_manager.is_user_admin(user_id):
        await message.answer("🚫 <b>У вас нет прав администратора.</b>")
        return
    
    args = message.text.split()
    if len(args) != 3:
        await message.answer("❌ Использование: /setrole &lt;user_id&gt; &lt;role&gt;\n\nДоступные роли: admin, user, guest")
        return
    
    try:
        target_user_id = int(args[1])
        new_role = args[2].lower()
    except ValueError:
        await message.answer("❌ Неверный ID пользователя")
        return
    
    if new_role not in ['admin', 'user', 'guest']:
        await message.answer("❌ Неверная роль. Доступные: admin, user, guest")
        return
    
    success = await user_manager.change_role(target_user_id, new_role, admin_id=user_id)
    if success:
        await message.answer(f"✅ Роль пользователя <code>{target_user_id}</code> изменена на <b>{new_role}</b>.")
    else:
        await message.answer(f"❌ Ошибка при изменении роли пользователя <code>{target_user_id}</code>")

@dp.message(Command("logs"))
async def view_logs_command(message: types.Message):
    """View logs (admin only)"""
    user_id = message.from_user.id
    if not await user_manager.is_user_admin(user_id):
        await message.answer("🚫 <b>У вас нет прав администратора.</b>")
        return
    
    args = message.text.split()
    
    if len(args) == 1:
        # Show all logs
        logs = await db.get_all_logs(limit=20)
        title = "📝 <b>Последние логи (все пользователи):</b>\n\n"
    else:
        # Show logs for specific user
        try:
            target_user_id = int(args[1])
        except ValueError:
            await message.answer("❌ Неверный ID пользователя")
            return
        logs = await db.get_user_logs(target_user_id, limit=20)
        title = f"📝 <b>Логи пользователя {target_user_id}:</b>\n\n"
    
    if not logs:
        await message.answer("📋 <b>Логи не найдены.</b>")
        return
    
    response = title
    for log in logs:
        response += f"🕒 {log.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n"
        response += f"👤 User: <code>{log.user_id}</code>\n"
        response += f"📄 {log.action}\n\n"
    
    await message.answer(response)

@dp.message(Command("userinfo"))
async def user_info_command(message: types.Message):
    """Get user information (admin only)"""
    user_id = message.from_user.id
    if not await user_manager.is_user_admin(user_id):
        await message.answer("🚫 <b>У вас нет прав администратора.</b>")
        return
    
    args = message.text.split()
    if len(args) != 2:
        await message.answer("❌ Использование: /userinfo &lt;user_id&gt;")
        return
    
    try:
        target_user_id = int(args[1])
    except ValueError:
        await message.answer("❌ Неверный ID пользователя")
        return
    
    user_info = await user_manager.get_user_info(target_user_id)
    if not user_info:
        await message.answer(f"❌ Пользователь <code>{target_user_id}</code> не найден")
        return
    
    status_emoji = "🚫" if user_info['status'] == "banned" else "✅"
    role_emoji = "👨‍💼" if user_info['role'] == "admin" else "👤"
    
    response = f"<b>👤 Информация о пользователе:</b>\n\n"
    response += f"{status_emoji} {role_emoji} <b>{user_info['name']}</b>\n\n"
    response += f"<b>ID:</b> <code>{user_info['id']}</code>\n"
    response += f"<b>Роль:</b> {user_info['role']}\n"
    response += f"<b>Статус:</b> {user_info['status']}\n"
    response += f"<b>Создан:</b> {user_info['created_at'].strftime('%Y-%m-%d %H:%M:%S')}\n"
    
    await message.answer(response)



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
    
    # Start scheduler for auto-posting
    scheduler = AsyncIOScheduler()
    scheduler.add_job(auto_post, 'interval', hours=6)
    scheduler.start()
    logger.info(f"🚀 Автопостинг запущен: каждые 6ч → {CHANNEL_ID}")

async def main():
    logger.info("✅ BOT v2.1 PRODUCTION READY!")
    await on_startup()
    try:
        await dp.start_polling(bot)
    finally:
        await db.close()
        logger.info("Bot shutdown complete")

if __name__ == "__main__":
    asyncio.run(main())
