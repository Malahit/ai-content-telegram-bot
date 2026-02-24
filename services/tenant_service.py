from __future__ import annotations

from sqlalchemy import select

from database.models import User, UserRole, UserStatus, Tenant, TenantStatus, Membership, MembershipRole


async def resolve_user_and_tenant(
    session,
    telegram_id: int,
    username: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
) -> tuple[int, int]:
    """Resolve a DB user.id and tenant.id for a telegram user.

    MVP behavior:
    - Ensure User exists for telegram_id (best-effort).
    - Ensure there is at least one tenant with a membership for that user.
      If none exists, create a default Tenant and OWNER Membership.

    Returns:
      (user_id, tenant_id)
    """

    # 1) User
    user = (await session.execute(select(User).where(User.telegram_id == telegram_id))).scalar_one_or_none()
    if user is None:
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            role=UserRole.USER,
            status=UserStatus.ACTIVE,
        )
        session.add(user)
        await session.flush()  # populate user.id

    # 2) Membership -> tenant
    membership = (
        await session.execute(select(Membership).where(Membership.user_id == user.id).order_by(Membership.id.asc()))
    ).scalar_one_or_none()

    if membership is not None:
        return user.id, membership.tenant_id

    # 3) Create default tenant
    tenant_name = f"Workspace {telegram_id}"
    tenant = Tenant(
        name=tenant_name,
        owner_user_id=user.id,
        status=TenantStatus.ACTIVE,
    )
    session.add(tenant)
    await session.flush()  # tenant.id

    session.add(
        Membership(
            tenant_id=tenant.id,
            user_id=user.id,
            role=MembershipRole.OWNER,
        )
    )

    await session.commit()
    return user.id, tenant.id
