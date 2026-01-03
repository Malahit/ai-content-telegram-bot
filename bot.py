import asyncio
import os
import random
from dotenv import load_dotenv
from langdetect import detect
from deep_translator import GoogleTranslator

from openai import OpenAI
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler


            translated = translator.translate(text, target_lang=target)

            return translated, target

        return text, detected

    except:

        return text, 'ru'

translator = GoogleTranslator(source='auto', target='ru')
async def detect_lang_and_translate(text, user_lang='ru'):
    """🌐 RU/EN перевод"""
    try:
        detected

# 🔥 RAG
try:
    from rag import create_vectorstore
    vectorstore = create_vectorstore()
    RAG_ENABLED = True
    print("✅ RAG активирован!")
except Exception as e:
    RAG_ENABLED = False
    vectorstore = None
    print(f"⚠️ RAG недоступен: {e}")

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
PPLX_API_KEY = os.getenv("PERPLEXITY_API_KEY")
CHANNEL_ID = "@content_ai_helper_bot"

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не найден!")

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📝 Пост"), KeyboardButton(text="❓ Помощь")]
    ],
    resize_keyboard=True,
)

@dp.message(CommandStart())
async def start_handler(message: types.Message):
    rag_status = "✅ RAG (твои файлы)" if RAG_ENABLED else "⚠️ Без RAG"
    await message.answer(
        f"<b>🚀 AI Content Bot v2.0 {rag_status} 🌐 RU/EN</b>\n\n"
        "Напиши тему поста — получи текст на твоем языке!\n\n"
        f"📡 Автопостинг: <code>{CHANNEL_ID}</code>",
        reply_markup=kb
    )

@dp.message(F.text.in_(["📝 Пост", "❓ Помощь"]))
async def menu_handler(message: types.Message):
    rag_status = "с твоими файлами" if RAG_ENABLED else "обычный"
    if message.text == "❓ Помощь":
        await message.answer(f"💬 Пиши тему поста — получи 250 слов {rag_status} с эмодзи!\n🌐 Авто RU/EN")
    else:
        await message.answer(f"✍️ Напиши тему поста ({rag_status})!")

@dp.message()
async def generate_post(message: types.Message):
    topic = message.text.strip()
    await message.answer(f"🔄 Генерирую пост про <b>{topic}</b>{' с RAG' if RAG_ENABLED else ''}... 🌐")

    if not PPLX_API_KEY:
        await message.answer("❌ PERPLEXITY_API_KEY в .env!")
        return

    client = OpenAI(
        api_key=PPLX_API_KEY,
        base_url="https://api.perplexity.ai",
        timeout=20.0,
    )

    # 🔥 RAG
    if RAG_ENABLED and vectorstore:
        relevant_docs = vectorstore.similarity_search(topic, k=2)
        context = "\n".join([doc.page_content[:500] for doc in relevant_docs])
        prompt = f'<b>КОНТЕКСТ:</b>\n{context}\n\nПост Telegram "{topic}": 250 слов, эмодзи, хук+CTA.'
        rag_info = f"\n📚 <i>{len(relevant_docs)} файлов</i>"
    else:
        prompt = f'Пост Telegram "{topic}": 250 слов, эмодзи, хук+CTA.'
        rag_info = ""

    try:
        response = client.chat.completions.create(
            model="sonar",
            messages=[
                {"role": "system", "content": "SMM-копирайтер Telegram."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=600,
            temperature=0.8,
        )
        
        post = response.choices[0].message.content.strip()
        
        # 🌐 МУЛЬТИЯЗЫК
        post_translated, lang = await detect_lang_and_translate(post)
        post_final = f"{post_translated}\n\n🌐 [{lang.upper()}]{rag_info}"
        
        await message.answer(f"<b>✨ Готовый пост:</b>\n\n{post_final}")
        print(f"✅ {topic} [{lang}] {'+RAG' if RAG_ENABLED else ''}")
        
    except Exception as e:
        post_error = f"<b>🔥 Пост про {topic}</b>{rag_info}\n\n[250 слов с эмодзи]\n<i>API: {str(e)[:50]}...</i>"
        await message.answer(post_error)
        print(f"❌ {e}")

# Автопостинг
async def auto_post():
    topics = ['фитнес', 'SMM', 'мотивация', 'питание']
    topic = random.choice(topics)
    try:
        # Имитируем message для generate_post
        fake_msg = types.Message(chat=types.Chat(id=0), text=topic, from_user=types.User(id=0))
        post = await generate_post(fake_msg)
        await bot.send_message(CHANNEL_ID, f"<b>🤖 Автопост:</b>\n\n{post}")
        print(f"✅ Автопост: {topic} → {CHANNEL_ID}")
    except Exception as e:
        print(f"❌ Автопост: {e}")

async def on_startup():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(auto_post, 'interval', hours=6)
    scheduler.start()
    print(f"🚀 Автопостинг запущен: каждые 6ч → {CHANNEL_ID}")

async def main():
    print("✅ BOT v2.0 ЗАПУЩЕН! RAG+" + ("ON" if RAG_ENABLED else "OFF"))
    await on_startup()  # ✅ Автопостинг старт
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())


