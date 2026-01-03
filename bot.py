import os
import asyncio
import requests
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message

BOT_TOKEN = os.getenv("BOT_TOKEN")
PPLX_API_KEY = os.getenv("PERPLEXITY_API_KEY")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def start_handler(message: Message):
    await message.answer("🤖 AI Content Bot v2.0 ✅\n📝 Напиши тему поста")

@dp.message()
async def generate_content(message: Message):
    topic = message.text
    
    headers = {
        "Authorization": f"Bearer {PPLX_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "sonar-pro",
        "messages": [{
            "role": "user", 
            "content": f"Создай пост для Telegram канала. 250 слов + эмодзи + CTA. Тема: {topic}"
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
        await message.answer(content[:4096])
        print(f"✅ Пост сгенерирован: {topic}")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)[:100]}")
        print(f"❌ Ошибка: {e}")

async def main():
    print("🚀 BOT ЗАПУЩЕН! v2.0")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
