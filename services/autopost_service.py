"""Сервис для управления подписками на автопостинг в каналы."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import AutopostSubscription
from logger_config import logger

AUTOPOST_PLANS = {
    "month": {
        "stars": 150,
        "days": 30,
        "label": "Месяц",
        "max_channels": 1,
        "description": "Автопостинг в 1 канал на 30 дней",
    },
    "half_year": {
        "stars": 750,
        "days": 180,
        "label": "Полгода",
        "max_channels": 3,
        "description": "Автопостинг до 3 каналов на 180 дней",
    },
    "year": {
        "stars": 1200,
        "days": 365,
        "label": "Год",
        "max_channels": 5,
        "description": "Автопостинг до 5 каналов на 365 дней",
    },
}

FREQUENCY_LABELS = {
    "daily": "1 раз в день",
    "twice_daily": "2 раза в день",
    "every_6h": "Каждые 6 часов",
    "weekly": "Раз в неделю",
}


async def create_autopost_subscription(
    session: AsyncSession,
    telegram_id: int,
    channel_id: str,
    channel_title: str,
    topic: str,
    frequency: str,
    send_hour_utc: int,
    send_hour_local: int,
    plan_type: str,
    stars_paid: int,
    telegram_charge_id: str = None,
    user_bot_token: str = None,
) -> AutopostSubscription:
    """Создать новую подписку на автопостинг."""
    plan = AUTOPOST_PLANS[plan_type]
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=plan["days"])

    sub = AutopostSubscription(
        telegram_id=telegram_id,
        channel_id=channel_id,
        channel_title=channel_title,
        topic=topic,
        frequency=frequency,
        send_hour_utc=send_hour_utc,
        send_hour_local=send_hour_local,
        plan_type=plan_type,
        stars_paid=stars_paid,
        telegram_charge_id=telegram_charge_id,
        is_active=True,
        expires_at=expires_at,
        user_bot_token=user_bot_token,
    )
    session.add(sub)
    await session.commit()
    await session.refresh(sub)
    logger.info(
        f"Autopost subscription created: user={telegram_id}, channel={channel_id}, "
        f"topic='{topic}', freq={frequency}, plan={plan_type}, "
        f"own_bot={'yes' if user_bot_token else 'no'}"
    )
    return sub


async def get_active_subscriptions(
    session: AsyncSession, telegram_id: int
) -> list[AutopostSubscription]:
    """Получить активные подписки пользователя."""
    result = await session.execute(
        select(AutopostSubscription).where(
            AutopostSubscription.telegram_id == telegram_id,
            AutopostSubscription.is_active == True,
        )
    )
    return result.scalars().all()


async def count_active_subscriptions_for_channel(
    session: AsyncSession, telegram_id: int
) -> int:
    """Подсчитать количество активных автопост-подписок пользователя."""
    result = await session.execute(
        select(AutopostSubscription).where(
            AutopostSubscription.telegram_id == telegram_id,
            AutopostSubscription.is_active == True,
        )
    )
    return len(result.scalars().all())


async def get_due_subscriptions(session: AsyncSession) -> list[AutopostSubscription]:
    """Получить подписки, для которых пора генерировать пост."""
    now = datetime.now(timezone.utc)
    current_hour = now.hour

    result = await session.execute(
        select(AutopostSubscription).where(
            AutopostSubscription.is_active == True,
            AutopostSubscription.expires_at > now,
        )
    )
    all_active = result.scalars().all()

    due = []
    for sub in all_active:
        if _is_due(sub, now, current_hour):
            due.append(sub)

    return due


def _is_due(sub: AutopostSubscription, now: datetime, current_hour: int) -> bool:
    """Проверить, пора ли генерировать пост для данной подписки."""
    if sub.frequency == "daily":
        if current_hour != sub.send_hour_utc:
            return False
        if sub.last_post_at and sub.last_post_at.date() >= now.date():
            return False
        return True

    elif sub.frequency == "twice_daily":
        second_hour = (sub.send_hour_utc + 12) % 24
        if current_hour not in (sub.send_hour_utc, second_hour):
            return False
        if sub.last_post_at:
            hours_since = (now - sub.last_post_at).total_seconds() / 3600
            if hours_since < 10:
                return False
        return True

    elif sub.frequency == "every_6h":
        valid_hours = [
            sub.send_hour_utc,
            (sub.send_hour_utc + 6) % 24,
            (sub.send_hour_utc + 12) % 24,
            (sub.send_hour_utc + 18) % 24,
        ]
        if current_hour not in valid_hours:
            return False
        if sub.last_post_at:
            hours_since = (now - sub.last_post_at).total_seconds() / 3600
            if hours_since < 5:
                return False
        return True

    elif sub.frequency == "weekly":
        if current_hour != sub.send_hour_utc:
            return False
        if sub.last_post_at:
            days_since = (now - sub.last_post_at).total_seconds() / 86400
            if days_since < 6:
                return False
        return True

    return False


async def deactivate_expired_subscriptions(session: AsyncSession) -> int:
    """Деактивировать просроченные подписки."""
    now = datetime.now(timezone.utc)
    result = await session.execute(
        update(AutopostSubscription)
        .where(
            AutopostSubscription.is_active == True,
            AutopostSubscription.expires_at <= now,
        )
        .values(is_active=False)
    )
    await session.commit()
    count = result.rowcount
    if count > 0:
        logger.info(f"Deactivated {count} expired autopost subscriptions")
    return count


async def cancel_subscription(
    session: AsyncSession, subscription_id: int, telegram_id: int
) -> bool:
    """Отменить подписку (по запросу пользователя)."""
    result = await session.execute(
        update(AutopostSubscription)
        .where(
            AutopostSubscription.id == subscription_id,
            AutopostSubscription.telegram_id == telegram_id,
        )
        .values(is_active=False)
    )
    await session.commit()
    if result.rowcount > 0:
        logger.info(f"Autopost subscription {subscription_id} cancelled by user {telegram_id}")
        return True
    return False


async def update_topic(
    session: AsyncSession, subscription_id: int, telegram_id: int, new_topic: str
) -> bool:
    """Обновить тему подписки."""
    result = await session.execute(
        update(AutopostSubscription)
        .where(
            AutopostSubscription.id == subscription_id,
            AutopostSubscription.telegram_id == telegram_id,
            AutopostSubscription.is_active == True,
        )
        .values(topic=new_topic)
    )
    await session.commit()
    if result.rowcount > 0:
        logger.info(
            f"Autopost subscription {subscription_id} topic updated to '{new_topic}'"
        )
        return True
    return False


async def update_last_post(session: AsyncSession, subscription_id: int):
    """Обновить last_post_at и posts_generated после публикации."""
    await session.execute(
        update(AutopostSubscription)
        .where(AutopostSubscription.id == subscription_id)
        .values(
            last_post_at=datetime.now(timezone.utc),
            posts_generated=AutopostSubscription.posts_generated + 1,
        )
    )
    await session.commit()


async def get_subscription_by_id(
    session: AsyncSession, subscription_id: int
) -> AutopostSubscription | None:
    """Получить подписку по ID."""
    result = await session.execute(
        select(AutopostSubscription).where(AutopostSubscription.id == subscription_id)
    )
    return result.scalar_one_or_none()
