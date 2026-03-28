from __future__ import annotations

from datetime import datetime, time, timezone

from sqlalchemy import select, func

from database.models import UsageEvent, UsageEventStatus
from database.database import AsyncSessionLocal


async def get_today_post_count(telegram_id: int) -> int:
    """Count successful posts by user today (UTC).

    Uses the UsageEvent table joined via user_id (internal PK)
    to count SUCCESS events created today.
    """
    from database.models import User

    now = datetime.now(timezone.utc)
    today_start = datetime.combine(now.date(), time.min, tzinfo=timezone.utc)

    async with AsyncSessionLocal() as session:
        # Resolve internal user_id from telegram_id
        user_result = await session.execute(
            select(User.id).where(User.telegram_id == telegram_id)
        )
        user_pk = user_result.scalar_one_or_none()
        if user_pk is None:
            return 0

        result = await session.execute(
            select(func.count(UsageEvent.id)).where(
                UsageEvent.user_id == user_pk,
                UsageEvent.status == UsageEventStatus.SUCCESS,
                UsageEvent.created_at >= today_start,
            )
        )
        return result.scalar() or 0


async def get_total_post_count(telegram_id: int) -> int:
    """Count all successful posts by user (all time)."""
    from database.models import User

    async with AsyncSessionLocal() as session:
        user_result = await session.execute(
            select(User.id).where(User.telegram_id == telegram_id)
        )
        user_pk = user_result.scalar_one_or_none()
        if user_pk is None:
            return 0

        result = await session.execute(
            select(func.count(UsageEvent.id)).where(
                UsageEvent.user_id == user_pk,
                UsageEvent.status == UsageEventStatus.SUCCESS,
            )
        )
        return result.scalar() or 0


async def record_usage_event(
    session,
    *,
    tenant_id: int,
    provider: str,
    status: str,
    model: str | None = None,
    user_id: int | None = None,
    channel_id: int | None = None,
    latency_ms: int | None = None,
    tokens_in: int | None = None,
    tokens_out: int | None = None,
    tokens_total: int | None = None,
    cost_usd: float = 0.0,
    error_code: str | None = None,
) -> None:
    st = status.lower()
    if st == "success":
        status_enum = UsageEventStatus.SUCCESS
    elif st == "blocked":
        status_enum = UsageEventStatus.BLOCKED
    else:
        status_enum = UsageEventStatus.FAILED

    ev = UsageEvent(
        tenant_id=tenant_id,
        channel_id=channel_id,
        user_id=user_id,
        provider=provider,
        model=model,
        status=status_enum,
        error_code=error_code,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        tokens_total=tokens_total,
        cost_usd=cost_usd,
        latency_ms=latency_ms,
    )
    session.add(ev)
    await session.commit()


async def record_blocked_usage_event(
    session,
    *,
    tenant_id: int,
    provider: str,
    reason: str,
    model: str | None = None,
    user_id: int | None = None,
    channel_id: int | None = None,
) -> None:
    await record_usage_event(
        session,
        tenant_id=tenant_id,
        provider=provider,
        model=model,
        user_id=user_id,
        channel_id=channel_id,
        status="blocked",
        cost_usd=0.0,
        error_code=reason,
    )
