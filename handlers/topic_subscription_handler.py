import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from database import get_session
from database.models import User, TopicSubscription
from services.user_service import UserService

logger = logging.getLogger(__name__)
router = Router()

AVAILABLE_TOPICS = [
    ("ai_tools", "🤖 AI инструменты"),
    ("content_marketing", "📢 Контент-маркетинг"),
    ("seo", "🔍 SEO"),
    ("social_media", "📱 Социальные сети"),
    ("copywriting", "✍️ Копирайтинг"),
    ("email_marketing", "📧 Email-маркетинг"),
    ("analytics", "📊 Аналитика"),
    ("design", "🎨 Дизайн"),
    ("video", "🎬 Видео"),
    ("automation", "⚙️ Автоматизация"),
]


def build_topics_keyboard(user_subscriptions: list[str]) -> InlineKeyboardMarkup:
    buttons = []
    for topic_key, topic_name in AVAILABLE_TOPICS:
        is_subscribed = topic_key in user_subscriptions
        status = "✅" if is_subscribed else "➕"
        buttons.append([
            InlineKeyboardButton(
                text=f"{status} {topic_name}",
                callback_data=f"topic_toggle:{topic_key}"
            )
        ])
    buttons.append([
        InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.message(Command("my_subscriptions"))
async def cmd_my_subscriptions(message: Message):
    user_id = message.from_user.id
    async with get_session() as session:
        result = await session.execute(
            select(TopicSubscription.topic).where(TopicSubscription.telegram_id == user_id)
        )
        subscriptions = [row[0] for row in result.fetchall()]

    keyboard = build_topics_keyboard(subscriptions)
    count = len(subscriptions)
    text = (
        f"📋 Ваши тематические подписки ({count}/{len(AVAILABLE_TOPICS)}):\n\n"
        f"Нажмите на тему, чтобы подписаться или отписаться.\n"
        f"Ежедневные посты приходят в 09:00 по вашему часовому поясу."
    )
    await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("topic_toggle:"))
async def toggle_topic_subscription(callback: CallbackQuery):
    topic_key = callback.data.split(":", 1)[1]
    user_id = callback.from_user.id

    topic_name = dict(AVAILABLE_TOPICS).get(topic_key, topic_key)

    async with get_session() as session:
        result = await session.execute(
            select(TopicSubscription).where(
                TopicSubscription.telegram_id == user_id,
                TopicSubscription.topic == topic_key
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            await session.delete(existing)
            await session.commit()
            action = "отписались от"
        else:
            new_sub = TopicSubscription(telegram_id=user_id, topic=topic_key)
            session.add(new_sub)
            await session.commit()
            action = "подписались на"

        # Refresh subscriptions
        result2 = await session.execute(
            select(TopicSubscription.topic).where(TopicSubscription.telegram_id == user_id)
        )
        subscriptions = [row[0] for row in result2.fetchall()]

    keyboard = build_topics_keyboard(subscriptions)
    count = len(subscriptions)
    text = (
        f"✅ Вы {action} тему: {topic_name}\n\n"
        f"📋 Ваши тематические подписки ({count}/{len(AVAILABLE_TOPICS)}):\n\n"
        f"Нажмите на тему, чтобы подписаться или отписаться.\n"
        "Управлять подписками: /my\_subscriptions"
    )
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "my_subscriptions")
async def show_subscriptions_from_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    async with get_session() as session:
        result = await session.execute(
            select(TopicSubscription.topic).where(TopicSubscription.telegram_id == user_id)
        )
        subscriptions = [row[0] for row in result.fetchall()]

    keyboard = build_topics_keyboard(subscriptions)
    count = len(subscriptions)
    text = (
        f"📋 Ваши тематические подписки ({count}/{len(AVAILABLE_TOPICS)}):\n\n"
        f"Нажмите на тему, чтобы подписаться или отписаться.\n"
        f"Ежедневные посты приходят каждый час согласно расписанию."
    )
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()
