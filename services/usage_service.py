from __future__ import annotations

from database.models import UsageEvent, UsageEventStatus


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
