📋 README.md — AI Content Telegram Bot

Цель проекта: AI-бот для генерации контента в Telegram (250 слов + эмодзи для каналов/блогов).
Статус: ✅ ОНАЙН (render.com + Perplexity Sonar Pro)
✅ СДЕЛАНО (3 Января 2026)
Шаг	Задача	Статус	Дата
A1	Telegram BOT_TOKEN	✅ 8125450571:AAFuC1v6k6xVqXw3z8w0jK0L0K5wZ0z0z0z	03.01
B1	GitHub SSH ключ	✅ ssh-ed25519 AAAAC3NzaC1lZDI1NTE5...	03.01
B2	git push origin main	✅ Everything up-to-date	03.01
C1	Perplexity PPLX_API_KEY	✅ pplx-... (у тебя есть)	03.01
D1	Render.com Dashboard	✅ ai-content-telegram-bot.onrender.com	03.01
D2	Environment Variables	✅ BOT_TOKEN + PPLX_API_KEY	03.01
E1	Manual Deploy	✅ "BOT ЗАПУЩЕН!" в Logs	03.01
E2	Тест в Telegram	✅ /start → "📝 Пост" → контент!	03.01
🔄 ТЕКУЩИЙ СОСТОЯНИЕ

text
GitHub: github.com/Malahit/ai-content-telegram-bot ✅
Render: ai-content-telegram-bot.onrender.com ✅
Telegram: @твой_бот → генерит посты ✅
Локально: ~/Projects_bot/ai-content-telegram-bot ✅

🚀 ПЛАН РАЗВИТИЯ
#	Фича	Сложность	Приоритет	Статус
1	RAG (загрузка твоих файлов в базу знаний)	⭐⭐⭐	Высокий	⏳
2	Автопостинг в канал по расписанию	⭐⭐	Высокий	⏳
3	Мультиязык RU/EN/DE посты	⭐	Средний	⏳
4	Аналитика (статистика постов)	⭐⭐	Средний	⏳
5	Custom Domain для бота	⭐	Низкий	⏳
📝 КОД БОТА (main.py)

python
BOT_TOKEN = os.getenv("BOT_TOKEN")  # Telegram
PPLX_API_KEY = os.getenv("PERPLEXITY_API_KEY")  # Perplexity Sonar
model="sonar"  # Pro модель
prompt: 250 слов + эмодзи + CTA

🎛️ УПРАВЛЕНИЕ

text
1. render.com → Logs (мониторинг)
2. Manual Deploy (обновить код)
3. Environment (ключи)
4. Telegram → /start → "📝 Пост" → "тема"
