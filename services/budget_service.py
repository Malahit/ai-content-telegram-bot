from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class BudgetStatus:
    allowed: bool
    should_warn: bool
    spend_usd: float
    hard_limit_usd: float | None
    warn_limit_usd: float | None


# Best-effort in-memory warning suppression.
# This resets on process restart (acceptable for MVP).
_last_warned_date_by_tenant: dict[int, str] = {}


def should_send_budget_warning(tenant_id: int) -> bool:
    today = datetime.now(timezone.utc).date().isoformat()
    last = _last_warned_date_by_tenant.get(tenant_id)
    return last != today


def mark_budget_warned(tenant_id: int) -> None:
    today = datetime.now(timezone.utc).date().isoformat()
    _last_warned_date_by_tenant[tenant_id] = today


async def check_tenant_budget(session, tenant_id: int) -> BudgetStatus:
    """Check monthly hard/warn budgets based on UsageEvent.cost_usd sum for current month."""

    from datetime import timedelta
    from decimal import Decimal

    from sqlalchemy import select, func

    from services.pricing_service import get_budget_hard_limit_usd, get_budget_warn_limit_usd
    from database.models import UsageEvent, UsageEventStatus

    now = datetime.now(timezone.utc)
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    # next month:
    if start.month == 12:
        end = start.replace(year=start.year + 1, month=1)
    else:
        end = start.replace(month=start.month + 1)

    hard_limit = get_budget_hard_limit_usd()
    warn_limit = get_budget_warn_limit_usd()

    stmt = (
        select(func.coalesce(func.sum(UsageEvent.cost_usd), 0))
        .where(UsageEvent.tenant_id == tenant_id)
        .where(UsageEvent.created_at >= start)
        .where(UsageEvent.created_at < end)
        .where(UsageEvent.status.in_([UsageEventStatus.SUCCESS, UsageEventStatus.FAILED]))
    )
    res = await session.execute(stmt)
    spend = res.scalar_one()

    # spend may be Decimal from Numeric column
    if isinstance(spend, Decimal):
        spend_usd = float(spend)
    else:
        spend_usd = float(spend or 0)

    allowed = True
    should_warn = False

    if hard_limit is not None and spend_usd >= hard_limit:
        allowed = False

    if warn_limit is not None and spend_usd >= warn_limit:
        should_warn = True

    return BudgetStatus(
        allowed=allowed,
        should_warn=should_warn,
        spend_usd=spend_usd,
        hard_limit_usd=hard_limit,
        warn_limit_usd=warn_limit,
    )
