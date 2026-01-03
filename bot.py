import os
import asyncio
import requests
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from rag.rag import RAGKnowledgeBase

# Ключи
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")  # Render переменная
PPLX_API_KEY = os.getenv("PPLX_API_KEY")

# Инициализация
rag_kb = RAGKnowledgeBase()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class ContentType(StatesGroup):
    POST = State()

@dp.message(Command("start"))
async def start_handler(message: Message):
    await message.answer(
        "🤖 AI Content Bot v2.0\n\n"
        "📝 Напиши тему поста:\n"
        "• SMM Москва\n"
        "• Быстрый завтрак\n\n"
        "📚 Загрузи PDF/DOCX → RAG база"
    )

@dp.message(Command("rag_status"))
async def rag_status(message: Message):
    status = "✅ Загружено" if rag_kb.vectorstore else "📚 Пусто"
    await message.answer(f"RAG: {status}")

@dp.message(lambda message: message.document)
async def upload_document(message: Message):
    file = await bot.get_file(message.document.file_id)
    file_path = f"rag/documents/{message.document.file_name}"

    await bot.download_file(file.file_path, file_path)
    await message.answer("📥 Файл загружен в RAG!")

    # Пересоздаём vectorstore
    docs = rag_kb.load_documents()
    rag_kb.create_vectorstore(docs)
    await message.answer("✅ RAG обновлён!")

@dp.message()
async def generate_content(message: Message, state: FSMContext):
    topic = message.text.strip()
    await message.answer(f"🔥 Генерирую пост для '{topic}'...")

    try:
        # ✅ ФИКС: безопасный RAG
        knowledge = ""
        if rag_kb.vectorstore:
            knowledge = rag_kb.search(topic)

        # Perplexity запрос вместо OpenAI
        url = "https://api.perplexity.ai/v1/chat"
        headers = {
            "Authorization": f"Bearer {PPLX_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "sonar",
            "messages": [
                {"role": "system", "content": "Создай SMM пост 200-300 слов. Эмодзи, структура, призыв к действию."},
                {"role": "user", "content": f"Тема: {topic}\nRAG: {knowledge}"}
            ],
            "max_tokens": 800,
            "temperature": 0.7
        }

        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()

        data = response.json()
        post_text = data.get("choices", [{}])[0].get("message", {}).get("content", "Ошибка: ответ пустой")

        await message.answer(f"✅ Пост готов!\n\n{post_text}")
        rag_status = "📚 RAG пуст" if not knowledge else "✅ RAG использован!"
        await message.answer(rag_status)

    except requests.exceptions.RequestException as e:
        await message.answer(f"❌ Ошибка: {str(e)}")

async def main():
    """Запуск бота"""
    print("🤖 Bot starting...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())