"""Сервис для управления подписками на ежедневные посты по теме."""
from datetime import datetime, timezone
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import TopicSubscription
from logger_config import logger

MAX_SUBSCRIPTIONS_PER_USER = 5


async def add_subscription(
    session: AsyncSession,
    telegram_id: int,
    topic: str,
    send_hour_utc: int = 8,
) -> tuple:
    """Добавить подписку. Возвращает (TopicSubscription | None, error_str)."""
    result = await session.execute(
        select(TopicSubscription).where(
            TopicSubscription.telegram_id == telegram_id,
            TopicSubscription.is_active == True,
        )
    )
    existing = result.scalars().all()
    if len(existing) >= MAX_SUBSCRIPTIONS_PER_USER:
        return None, f"Максимум {MAX_SUBSCRIPTIONS_PER_USER} активных подписок"
    for sub in existing:
        if sub.topic.lower() == topic.lower():
            return None, f'Подписка на тему «{topic}» уже существует'
    sub = TopicSubscription(
        telegram_id=telegram_id,
        topic=topic,
        send_hour_utc=send_hour_utc,
        is_active=True,
    )
    session.add(sub)
    await session.commit()
    await session.refresh(sub)
    logger.info(f"User {telegram_id} subscribed to topic: '{topic}'")
    return sub, ""


async def get_user_subscriptions(session: AsyncSession, telegram_id: int) -> list:
    """Список активных подписок пользователя."""
    result = await session.execute(
        select(TopicSubscription).where(
            TopicSubscription.telegram_id == telegram_id,
            TopicSubscription.is_active == True,
        )
    )
    return result.scalars().all()


async def cancel_subscription(
    session: AsyncSession, subscription_id: int, telegram_id: int
) -> bool:
    """Деактивировать подписку."""
    result = await session.execute(
        update(TopicSubscription)
        .where(
            TopicSubscription.id == subscription_id,
            TopicSubscription.telegram_id == telegram_id,
        )
        .values(is_active=False)
    )
    await session.commit()
    return result.rowcount > 0


async def get_all_active_subscriptions(session: AsyncSession) -> list:
    """Все активные подписки (для планировщика)."""
    result = await session.execute(
        select(TopicSubscription).where(TopicSubscription.is_active == True)
    )
    return result.scalars().all()


async def mark_sent(session: AsyncSession, subscription_id: int):
    """Обновить last_sent_at = now(UTC)."""
    await session.execute(
        update(TopicSubscription)
        .where(TopicSubscription.id == subscription_id)
        .values(last_sent_at=datetime.now(timezone.utc))
    )
    await session.commit()
