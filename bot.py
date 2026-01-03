import os
import asyncio
import requests
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from rag.rag import RAGKnowledgeBase

BOT_TOKEN = os.getenv("BOT_TOKEN")
PPLX_API_KEY = os.getenv("PERPLEXITY_API_KEY")

# RAG база знаний
rag_kb = RAGKnowledgeBase()

bot = Bot(token=BOT_TOKEN)

dp = Dispatcher()

@dp.message(Command("start"))
async def start_handler(message: Message):
    await message.answer("🤖 AI Content Bot v2.0\n📝 Напиши тему поста")

@dp.message()
async def generate_content(message: Message):
    topic = message.text
    
    # Ищем в базе знаний
    try:
        knowledge = rag_kb.search(topic)
        context = f"База знаний: {knowledge[:1000]}" if knowledge else "Нет релевантных документов"
    except:
        context = "RAG недоступен"
    
    headers = {
        "Authorization": f"Bearer {PPLX_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "sonar-pro",
        "messages": [{
            "role": "user", 
            "content": f"""Создай пост для Telegram канала. 250 слов + эмодзи + CTA.

ТЕМА: {topic}

КОНТЕКСТ ИЗ ТВОИХ ДОКУМЕНТОВ:
{context}

Сделай пост персонализированным!"""
        }]
    }
    
    try:
        response = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )
        result = response.json()
        content = result['choices'][0]['message']['content']
        rag_info = f"📚 RAG: {knowledge[:150]}..." if knowledge else "📚 RAG пуст"
        await message.answer(f"{rag_info}\n\n{content[:3800]}")
        print(f"✅ RAG пост: {topic}")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)[:100]}")

if __name__ == "__main__":
    asyncio.run(main())

