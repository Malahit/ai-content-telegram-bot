import asyncio
import logging
import os
import random
import requests
from dotenv import load_dotenv
from typing import Optional
from bot_statistics import stats_tracker
from image_fetcher import image_fetcher

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
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InputMediaPhoto
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
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
UNSPLASH_API_KEY = os.getenv("UNSPLASH_API_KEY")  # API key for Unsplash
ADMIN_USER_IDS = os.getenv("ADMIN_USER_IDS", "").split(",")  # Comma-separated admin IDs
ADMIN_USER_IDS = [int(uid.strip()) for uid in ADMIN_USER_IDS if uid.strip().isdigit()]

if not BOT_TOKEN:
    raise RuntimeError("❌ BOT_TOKEN не найден в .env!")
if not PPLX_API_KEY:
    raise RuntimeError("❌ PPLX_API_KEY не найден в .env!")

print(f"🚀 BOT_TOKEN: ✅ | PPLX_API_KEY: ✅ | CHANNEL_ID: {CHANNEL_ID}")
print(f"✅ RAG: {'ON' if RAG_ENABLED else 'OFF'} | 🌐 Translate: {'ON' if TRANSLATE_ENABLED else 'OFF'}")
print(f"🖼️ Unsplash: {'ON' if UNSPLASH_API_KEY else 'OFF'} | 👥 Admins: {len(ADMIN_USER_IDS)}")

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
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
    images_status = "🖼️ Images" if UNSPLASH_API_KEY else ""
    user_keyboard = get_keyboard(message.from_user.id)
    
    await message.answer(
        f"<b>🚀 AI Content Bot v2.2 PROD {rag_status} {translate_status} {images_status}</b>\n\n"
        f"💬 <i>Тема поста → готовый текст 200-300 слов!</i>\n\n"
        f"📝 <b>Пост</b> - только текст\n"
        f"🖼️ <b>Пост с фото</b> - текст + до 3 изображений\n\n"
        f"📡 Автопостинг: <code>{CHANNEL_ID}</code> (каждые 6ч)\n"
        f"⚙️ max_tokens=800 | sonar-small-online\n\n"
        f"<b>Примеры:</b> SMM Москва | фитнес | завтрак",
        reply_markup=user_keyboard
    )

@dp.message(F.text.in_({"📝 Пост", "🖼️ Пост с фото", "❓ Помощь", "ℹ️ Статус", "📊 Статистика"}))
async def menu_handler(message: types.Message, state: FSMContext):
    rag_status = "с RAG" if RAG_ENABLED else "обычный"
    if message.text == "❓ Помощь":
        await state.clear()  # Clear any active state
        await message.answer(
            f"🎯 <b>Как использовать:</b>\n"
            f"• 📝 <b>Пост</b> - только текст\n"
            f"• 🖼️ <b>Пост с фото</b> - текст + 3 изображения\n"
            f"• Пиши тему, получи готовый контент!\n"
            f"• 🌐 Авто RU/EN перевод\n\n"
            f"<b>Команды:</b> /start\n"
            f"<code>Техподдержка: @твой_nick</code>"
        )
    elif message.text == "ℹ️ Статус":
        await state.clear()  # Clear any active state
        await message.answer(
            f"✅ Bot: Online\n"
            f"✅ Perplexity: sonar-small-online\n"
            f"📚 RAG: {'ON' if RAG_ENABLED else 'OFF'}\n"
            f"🌐 Translate: {'ON' if TRANSLATE_ENABLED else 'OFF'}\n"
            f"🖼️ Images: {'ON' if UNSPLASH_API_KEY else 'OFF'}\n"
            f"⏰ Автопост: каждые 6ч → {CHANNEL_ID}"
        )
    elif message.text == "📊 Статистика":
        await state.clear()  # Clear any active state
        # Admin-only feature
        if message.from_user.id not in ADMIN_USER_IDS:
            await message.answer("❌ <b>Доступ запрещён!</b> Эта функция только для администраторов.")
            return
        
        report = stats_tracker.get_report()
        await message.answer(report)
    else:
        # Handle "📝 Пост" or "🖼️ Пост с фото"
        post_type = "images" if message.text == "🖼️ Пост с фото" else "text"
        await state.update_data(post_type=post_type)
        await state.set_state(PostGeneration.waiting_for_topic)
        await message.answer(f"✍️ <b>Напиши тему поста</b> ({rag_status})!")

@dp.message(PostGeneration.waiting_for_topic)
async def generate_post(message: types.Message, state: FSMContext):
    topic = message.text.strip()
    user_id = message.from_user.id
    
    # Get the post type from state
    data = await state.get_data()
    post_type = data.get("post_type", "text")
    
    await message.answer(f"<b>🔄 Генерирую</b> пост про <i>{topic}</i>{' +RAG' if RAG_ENABLED else ''}... ⏳10-20с")
    
    # Generate content
    content = await generate_content(topic)
    
    # Track statistics
    stats_tracker.record_post(user_id, topic, post_type)
    
    if post_type == "images" and UNSPLASH_API_KEY:
        # Fetch images for the post
        await message.answer("🖼️ Ищу подходящие изображения...")
        try:
            image_urls = await image_fetcher.search_images(topic, max_images=3)
        except Exception as e:
            logger.error(f"Image fetching failed completely: {e}")
            image_urls = []
            # Inform admin users about the failure
            if user_id in ADMIN_USER_IDS:
                await message.answer(f"⚠️ <b>Admin Notice:</b> Image API failure - {str(e)[:100]}")
        
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
                logger.error(f"Error sending images to Telegram: {e}")
                # Fallback to text-only
                error_msg = f"<b>✨ Готовый пост:</b>\n\n{content}\n\n⚠️ Ошибка отправки изображений"
                if user_id in ADMIN_USER_IDS:
                    error_msg += f"\n🔧 Причина: {str(e)[:100]}"
                await message.answer(error_msg)
        else:
            # No images found, send text only
            error_msg = f"<b>✨ Готовый пост:</b>\n\n{content}\n\n⚠️ Изображения не найдены"
            if user_id in ADMIN_USER_IDS:
                error_msg += "\n🔧 Все API сервисы недоступны или не настроены"
            await message.answer(error_msg)
    else:
        # Text-only post
        await message.answer(f"<b>✨ Готовый пост:</b>\n\n{content}")
    
    # Clear state
    await state.clear()

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
