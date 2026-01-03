import asyncio
import os
from dotenv import load_dotenv

from openai import OpenAI
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

# 🔥 RAG ИМПОРТ (новое)
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
        f"<b>🚀 AI Content Bot {rag_status}</b>\n\n"
        "Напиши тему поста — получи текст!",
        reply_markup=kb
    )

@dp.message(F.text.in_(["📝 Пост", "❓ Помощь"]))
async def menu_handler(message: types.Message):
    rag_status = "с твоими файлами" if RAG_ENABLED else "обычный"
    if message.text == "❓ Помощь":
        await message.answer(f"Пиши тему поста — получи 250 слов {rag_status} с эмодзи!")
    else:
        await message.answer(f"Напиши тему поста ({rag_status})!")

@dp.message()
async def generate_post(message: types.Message):
    topic = message.text.strip()
    await message.answer(f"🔄 Генерирую пост про <b>{topic}</b>{' с RAG' if RAG_ENABLED else ''}...")

    if not PPLX_API_KEY:
        await message.answer("❌ Добавь PERPLEXITY_API_KEY в .env!")
        return

    client = OpenAI(
        api_key=PPLX_API_KEY,
        base_url="https://api.perplexity.ai",
        timeout=20.0,
    )

    # 🔥 RAG ПРОМПТ (обновлено)
    if RAG_ENABLED and vectorstore:
        relevant_docs = vectorstore.similarity_search(topic, k=2)
        context = "\n".join([doc.page_content[:500] for doc in relevant_docs])  # 500 символов
        prompt = f'<b>КОНТЕКСТ ИЗ ТВОИХ ФАЙЛОВ:</b>\n{context}\n\nСоздай пост для Telegram на тему "{topic}": 250 слов, эмодзи, хук+CTA, живой стиль.'
        rag_info = f"\n\n📚 <i>Контекст: {len(relevant_docs)} файлов</i>"
    else:
        prompt = f'Создай пост для Telegram на тему "{topic}": 250 слов, эмодзи, хук+CTA, живой стиль.'
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
        await message.answer(f"<b>✨ Готовый пост:{rag_info}</b>\n\n{post}")
        print(f"✅ Успех: {topic} {'+RAG' if RAG_ENABLED else ''}")
        
    except Exception as e:
        await message.answer(
            f"🔥 <b>Пост про {topic}</b>{rag_info}\n\n"
            f"[250 слов с эмодзи]\n\n"
            f"<i>API: {str(e)[:50]}...</i>"
        )
        print(f"❌ {e}")

async def main():
    print("✅ BOT ЗАПУЩЕН!" + (" + RAG" if RAG_ENABLED else ""))
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

