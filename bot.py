import asyncio
import logging
import os
import random
import re
import requests
from dotenv import load_dotenv
from typing import Optional

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

def clean_text(content: str) -> str:
    """🧹 Sanitize generated content by removing artifacts"""
    # Remove links starting with http or www
    content = re.sub(r"https?://\S+|www\.\S+", "", content)
    # Remove numbers in brackets or parentheses (e.g., [123] or (123))
    content = re.sub(r"\[\d+\]|\(\d+\)", "", content)
    # Remove extra spaces and trim
    content = re.sub(r"\s+", " ", content).strip()
    return content

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
        
        # 🧹 Clean the content
        content = clean_text(content)
        
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
