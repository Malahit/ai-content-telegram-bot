import asyncio
import logging
import os
import random
import requests
from dotenv import load_dotenv
from typing import Optional
from bot_statistics import stats_tracker
from image_fetcher import image_fetcher

# Yandex Wordstat integration
try:
    from wordstat_parser import wordstat_parser
    from seo_post_generator import SEOPostGenerator
    WORDSTAT_ENABLED = True
    print("✅ Yandex Wordstat активирован!")
except ImportError:
    WORDSTAT_ENABLED = False
    wordstat_parser = None
    SEOPostGenerator = None
    print("⚠️ Wordstat недоступен")

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
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InputMediaPhoto, InlineKeyboardMarkup, InlineKeyboardButton
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
print(f"📊 Wordstat: {'ON' if WORDSTAT_ENABLED else 'OFF'}")

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

# Initialize SEO post generator if Wordstat is enabled
seo_generator = SEOPostGenerator(PPLX_API_KEY) if WORDSTAT_ENABLED else None

# FSM States for post generation
class PostGeneration(StatesGroup):
    waiting_for_topic = State()
    post_type = State()  # "text" or "images"

# FSM States for Wordstat
class WordstatState(StatesGroup):
    waiting_for_keyword = State()
    showing_results = State()

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

# Wordstat command handler
@dp.message(Command("wordstat"))
async def wordstat_command(message: types.Message, state: FSMContext):
    """Handle /wordstat command"""
    if not WORDSTAT_ENABLED:
        await message.answer("❌ <b>Wordstat недоступен!</b>\n\nУстановите необходимые зависимости: selenium, webdriver-manager, tenacity")
        return
    
    # Get keyword from command or ask for it
    command_parts = message.text.split(maxsplit=1)
    
    if len(command_parts) > 1:
        # Keyword provided with command
        keyword = command_parts[1].strip()
        await process_wordstat_keyword(message, keyword, state)
    else:
        # Ask for keyword
        await state.set_state(WordstatState.waiting_for_keyword)
        await message.answer(
            "🔍 <b>Yandex Wordstat</b>\n\n"
            "Введите ключевое слово для анализа:\n"
            "<i>Например: фитнес, SMM, недвижимость</i>"
        )

@dp.message(WordstatState.waiting_for_keyword)
async def wordstat_keyword_input(message: types.Message, state: FSMContext):
    """Handle keyword input for Wordstat"""
    keyword = message.text.strip()
    await process_wordstat_keyword(message, keyword, state)

async def process_wordstat_keyword(message: types.Message, keyword: str, state: FSMContext):
    """Process Wordstat request for a keyword"""
    # Send processing message
    processing_msg = await message.answer(
        f"🔍 <b>Анализирую запрос:</b> <i>{keyword}</i>\n\n"
        "⏳ Это может занять 10-30 секунд..."
    )
    
    try:
        # Get Wordstat data
        wordstat_data = wordstat_parser.get_wordstat_data(keyword)
        
        # Store data in state for later use
        await state.update_data(
            keyword=keyword,
            wordstat_data=wordstat_data
        )
        await state.set_state(WordstatState.showing_results)
        
        # Format results
        search_volume = wordstat_data.get("search_volume", "N/A")
        related_keywords = wordstat_data.get("related_keywords", [])
        error = wordstat_data.get("error")
        
        result_text = f"📊 <b>Yandex Wordstat - Результаты</b>\n\n"
        result_text += f"🔑 <b>Ключевое слово:</b> {keyword}\n"
        result_text += f"📈 <b>Запросов в месяц:</b> {search_volume}\n"
        
        if related_keywords:
            result_text += f"\n🔗 <b>Связанные запросы ({len(related_keywords)}):</b>\n"
            for i, kw in enumerate(related_keywords[:10], 1):
                result_text += f"{i}. {kw}\n"
        
        if error:
            result_text += f"\n⚠️ <i>Частичные данные (ошибка парсинга)</i>"
        
        # Create inline keyboard
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✍️ Создать SEO пост",
                    callback_data="wordstat_seo"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔄 Обновить данные",
                    callback_data="wordstat_retry"
                )
            ]
        ])
        
        # Delete processing message and send results
        await processing_msg.delete()
        await message.answer(result_text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Error processing Wordstat request: {e}")
        await processing_msg.edit_text(
            f"❌ <b>Ошибка получения данных</b>\n\n"
            f"<i>{str(e)[:200]}</i>\n\n"
            "Попробуйте другое ключевое слово или повторите позже."
        )
        await state.clear()

# Callback handler for "Generate SEO Post"
@dp.callback_query(F.data.startswith("wordstat_seo_"))
async def wordstat_generate_seo(callback: types.CallbackQuery, state: FSMContext):
    """Handle Generate SEO Post button"""
    await callback.answer()
    
    # Extract keyword from callback data
    keyword = callback.data.replace("wordstat_seo_", "")
    
    # Get wordstat data from state
    data = await state.get_data()
    wordstat_data = data.get("wordstat_data")
    
    if not wordstat_data:
        await callback.message.answer("❌ Данные не найдены. Используйте /wordstat снова.")
        await state.clear()
        return
    
    # Send generating message
    await callback.message.answer(
        f"✍️ <b>Генерирую SEO-пост...</b>\n\n"
        f"🔑 Ключевое слово: <i>{keyword}</i>\n"
        f"⏳ Подождите 15-30 секунд..."
    )
    
    try:
        # Generate SEO post
        seo_post = seo_generator.generate_seo_post(keyword, wordstat_data)
        
        # Send the post
        await callback.message.answer(
            f"<b>✨ SEO-пост готов:</b>\n\n{seo_post}"
        )
        
        # Clear state
        await state.clear()
        
    except Exception as e:
        logger.error(f"Error generating SEO post: {e}")
        await callback.message.answer(
            f"❌ <b>Ошибка генерации SEO-поста</b>\n\n"
            f"<i>{str(e)[:200]}</i>"
        )

# Callback handler for "Retry for Data"
@dp.callback_query(F.data.startswith("wordstat_retry_"))
async def wordstat_retry(callback: types.CallbackQuery, state: FSMContext):
    """Handle Retry for Data button"""
    await callback.answer("🔄 Обновляю данные...")
    
    # Extract keyword from callback data
    keyword = callback.data.replace("wordstat_retry_", "")
    
    # Process keyword again (force fresh data)
    await process_wordstat_keyword(callback.message, keyword, state)


@dp.message(CommandStart())
async def start_handler(message: types.Message):
    rag_status = "✅ RAG" if RAG_ENABLED else "⚠️ Без RAG"
    translate_status = "🌐 RU/EN" if TRANSLATE_ENABLED else ""
    images_status = "🖼️ Images" if UNSPLASH_API_KEY else ""
    wordstat_status = "📊 Wordstat" if WORDSTAT_ENABLED else ""
    user_keyboard = get_keyboard(message.from_user.id)
    
    wordstat_info = ""
    if WORDSTAT_ENABLED:
        wordstat_info = f"\n📊 <b>/wordstat [ключ]</b> - SEO анализ Яндекс.Вордстат\n"
    
    await message.answer(
        f"<b>🚀 AI Content Bot v2.3 PROD {rag_status} {translate_status} {images_status} {wordstat_status}</b>\n\n"
        f"💬 <i>Тема поста → готовый текст 200-300 слов!</i>\n\n"
        f"📝 <b>Пост</b> - только текст\n"
        f"🖼️ <b>Пост с фото</b> - текст + до 3 изображений{wordstat_info}\n"
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
        wordstat_help = ""
        if WORDSTAT_ENABLED:
            wordstat_help = f"• 📊 <b>/wordstat [ключ]</b> - SEO анализ\n"
        await message.answer(
            f"🎯 <b>Как использовать:</b>\n"
            f"• 📝 <b>Пост</b> - только текст\n"
            f"• 🖼️ <b>Пост с фото</b> - текст + 3 изображения\n"
            f"{wordstat_help}"
            f"• Пиши тему, получи готовый контент!\n"
            f"• 🌐 Авто RU/EN перевод\n\n"
            f"<b>Команды:</b> /start{', /wordstat' if WORDSTAT_ENABLED else ''}\n"
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
            f"📊 Wordstat: {'ON' if WORDSTAT_ENABLED else 'OFF'}\n"
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
        image_urls = image_fetcher.search_images(topic, max_images=3)
        
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
                logger.error(f"Error sending images: {e}")
                # Fallback to text-only
                await message.answer(f"<b>✨ Готовый пост:</b>\n\n{content}\n\n⚠️ Ошибка загрузки изображений")
        else:
            # No images found, send text only
            await message.answer(f"<b>✨ Готовый пост:</b>\n\n{content}\n\n⚠️ Изображения не найдены")
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
