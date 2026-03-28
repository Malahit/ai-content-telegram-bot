"""
Database models for AI Content Telegram Bot.

This module contains core entities (users, payments, logs) and SaaS foundations
(tenants/workspaces, memberships, channels, usage events).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, List
import enum

from sqlalchemy import (
    BigInteger,
    Boolean,
    Integer,
    String,
    DateTime,
    JSON,
    Numeric,
    Enum as SQLEnum,
    ForeignKey,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all models."""

    pass


# -----------------
# Core / existing
# -----------------


class PaymentStatus(enum.Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"


class UserRole(enum.Enum):
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"


class UserStatus(enum.Enum):
    ACTIVE = "active"
    BANNED = "banned"


class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("telegram_id", name="uq_users_telegram_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    subscription_end: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    role: Mapped[UserRole] = mapped_column(
        SQLEnum(UserRole, native_enum=False), default=UserRole.USER, nullable=False
    )
    status: Mapped[UserStatus] = mapped_column(
        SQLEnum(UserStatus, native_enum=False), default=UserStatus.ACTIVE, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    payments: Mapped[List["Payment"]] = relationship(
        "Payment", back_populates="user", cascade="all, delete-orphan"
    )
    logs: Mapped[List["Log"]] = relationship(
        "Log", back_populates="user", cascade="all, delete-orphan"
    )

    # SaaS
    owned_tenants: Mapped[List["Tenant"]] = relationship(
        "Tenant", back_populates="owner_user", cascade="all"
    )
    memberships: Mapped[List["Membership"]] = relationship(
        "Membership", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return (
            f"<User(id={self.id}, telegram_id={self.telegram_id}, "
            f"role={self.role.value}, status={self.status.value})>"
        )


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(
        SQLEnum(PaymentStatus, native_enum=False),
        default=PaymentStatus.PENDING,
        nullable=False,
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="payments")

    def __repr__(self) -> str:
        return (
            f"<Payment(id={self.id}, user_id={self.user_id}, amount={self.amount}, "
            f"status={self.status.value})>"
        )


class Log(Base):
    __tablename__ = "logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    action: Mapped[str] = mapped_column(String(500), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False, index=True
    )

    user: Mapped["User"] = relationship("User", back_populates="logs")

    def __repr__(self) -> str:
        short = (self.action[:47] + "...") if len(self.action) > 50 else self.action
        return f"<Log(id={self.id}, user_id={self.user_id}, action='{short}')>"


# -----------------
# SaaS foundations
# -----------------


class TenantStatus(enum.Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"


class MembershipRole(enum.Enum):
    OWNER = "owner"
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    owner_user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[TenantStatus] = mapped_column(
        SQLEnum(TenantStatus, native_enum=False), default=TenantStatus.ACTIVE, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    owner_user: Mapped["User"] = relationship("User", back_populates="owned_tenants")
    memberships: Mapped[List["Membership"]] = relationship(
        "Membership", back_populates="tenant", cascade="all, delete-orphan"
    )
    channels: Mapped[List["Channel"]] = relationship(
        "Channel", back_populates="tenant", cascade="all, delete-orphan"
    )
    usage_events: Mapped[List["UsageEvent"]] = relationship(
        "UsageEvent", back_populates="tenant", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Tenant(id={self.id}, owner_user_id={self.owner_user_id}, status={self.status.value})>"


class Membership(Base):
    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("tenant_id", "user_id", name="uq_memberships_tenant_user"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[MembershipRole] = mapped_column(
        SQLEnum(MembershipRole, native_enum=False),
        default=MembershipRole.OWNER,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="memberships")
    user: Mapped["User"] = relationship("User", back_populates="memberships")

    def __repr__(self) -> str:
        return f"<Membership(id={self.id}, tenant_id={self.tenant_id}, user_id={self.user_id}, role={self.role.value})>"


class Channel(Base):
    __tablename__ = "channels"
    __table_args__ = (
        UniqueConstraint("tenant_id", "telegram_channel_id", name="uq_channels_tenant_channel_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    telegram_channel_id: Mapped[str] = mapped_column(String(255), nullable=False)
    channel_username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    language_default: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)

    autopost_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    autopost_interval_hours: Mapped[int] = mapped_column(Integer, default=6, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="channels")
    usage_events: Mapped[List["UsageEvent"]] = relationship(
        "UsageEvent", back_populates="channel", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Channel(id={self.id}, tenant_id={self.tenant_id}, telegram_channel_id={self.telegram_channel_id})>"


class UsageEventStatus(enum.Enum):
    SUCCESS = "success"
    FAILED = "failed"
    BLOCKED = "blocked"


class UsageEvent(Base):
    __tablename__ = "usage_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    channel_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("channels.id", ondelete="SET NULL"), nullable=True, index=True
    )
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    provider: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    status: Mapped[UsageEventStatus] = mapped_column(
        SQLEnum(UsageEventStatus, native_enum=False),
        default=UsageEventStatus.SUCCESS,
        nullable=False,
        index=True,
    )

    error_code: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    tokens_in: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    tokens_out: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    tokens_total: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    cost_usd: Mapped[float] = mapped_column(Numeric(10, 6), default=0, nullable=False)
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="usage_events")
    channel: Mapped[Optional["Channel"]] = relationship("Channel", back_populates="usage_events")

    def __repr__(self) -> str:
        return (
            f"<UsageEvent(id={self.id}, tenant_id={self.tenant_id}, provider={self.provider}, "
            f"status={self.status.value}, cost_usd={self.cost_usd})>"
        )


# -----------------
# Topic Subscriptions
# -----------------


class TopicSubscription(Base):
    """Подписка пользователя на ежедневные посты по теме."""
    __tablename__ = "topic_subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    topic: Mapped[str] = mapped_column(String(500), nullable=False)
    send_hour_utc: Mapped[int] = mapped_column(Integer, default=8, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    last_sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return (
            f"<TopicSubscription(id={self.id}, telegram_id={self.telegram_id}, "
            f"topic='{self.topic}', hour={self.send_hour_utc})>"
        )


# -----------------
# Autopost Subscriptions
# -----------------


class AutopostSubscription(Base):
    """Подписка на автоматическую публикацию постов в TG-канал по расписанию."""
    __tablename__ = "autopost_subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    channel_id: Mapped[str] = mapped_column(String(100), nullable=False)
    channel_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    topic: Mapped[str] = mapped_column(String(500), nullable=False)
    frequency: Mapped[str] = mapped_column(String(50), nullable=False)
    send_hour_utc: Mapped[int] = mapped_column(Integer, nullable=False)
    send_hour_local: Mapped[int] = mapped_column(Integer, nullable=False)
    timezone: Mapped[str] = mapped_column(String(50), default="Europe/Moscow", nullable=False)
    plan_type: Mapped[str] = mapped_column(String(20), nullable=False)
    stars_paid: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    telegram_charge_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    starts_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_post_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    posts_generated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )

    def __repr__(self) -> str:
        return (
            f"<AutopostSubscription(id={self.id}, telegram_id={self.telegram_id}, "
            f"channel={self.channel_id}, topic='{self.topic}', freq={self.frequency})>"
        )
