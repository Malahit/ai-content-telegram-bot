"""Add SaaS multi-tenant foundations and usage metering tables

Revision ID: saas_multitenant_usage
Revises: add_role_status_logs
Create Date: 2026-02-25 00:46:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "saas_multitenant_usage"
down_revision: Union[str, None] = "add_role_status_logs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Tenants
    op.create_table(
        "tenants",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("owner_user_id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("ACTIVE", "SUSPENDED", name="tenantstatus"),
            nullable=False,
            server_default="ACTIVE",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_tenants_owner_user_id"), "tenants", ["owner_user_id"], unique=False)

    # Memberships
    op.create_table(
        "memberships",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "role",
            sa.Enum("OWNER", "ADMIN", "EDITOR", "VIEWER", name="membershiprole"),
            nullable=False,
            server_default="OWNER",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "user_id", name="uq_memberships_tenant_user"),
    )
    op.create_index(op.f("ix_memberships_tenant_id"), "memberships", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_memberships_user_id"), "memberships", ["user_id"], unique=False)

    # Channels
    op.create_table(
        "channels",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("telegram_channel_id", sa.String(length=255), nullable=False),
        sa.Column("channel_username", sa.String(length=255), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("language_default", sa.String(length=16), nullable=True),
        sa.Column("autopost_enabled", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("autopost_interval_hours", sa.Integer(), nullable=False, server_default="6"),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "telegram_channel_id", name="uq_channels_tenant_channel_id"),
    )
    op.create_index(op.f("ix_channels_tenant_id"), "channels", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_channels_channel_username"), "channels", ["channel_username"], unique=False)

    # Usage events
    op.create_table(
        "usage_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("channel_id", sa.Integer(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=True),
        sa.Column(
            "status",
            sa.Enum("SUCCESS", "FAILED", "BLOCKED", name="usageeventstatus"),
            nullable=False,
            server_default="SUCCESS",
        ),
        sa.Column("error_code", sa.String(length=128), nullable=True),
        sa.Column("tokens_in", sa.Integer(), nullable=True),
        sa.Column("tokens_out", sa.Integer(), nullable=True),
        sa.Column("tokens_total", sa.Integer(), nullable=True),
        sa.Column(
            "cost_usd",
            sa.Numeric(10, 6),
            nullable=False,
            server_default="0",
        ),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["channel_id"], ["channels.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_usage_events_tenant_id"), "usage_events", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_usage_events_channel_id"), "usage_events", ["channel_id"], unique=False)
    op.create_index(op.f("ix_usage_events_user_id"), "usage_events", ["user_id"], unique=False)
    op.create_index(op.f("ix_usage_events_provider"), "usage_events", ["provider"], unique=False)
    op.create_index(op.f("ix_usage_events_status"), "usage_events", ["status"], unique=False)
    op.create_index(op.f("ix_usage_events_created_at"), "usage_events", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_usage_events_created_at"), table_name="usage_events")
    op.drop_index(op.f("ix_usage_events_status"), table_name="usage_events")
    op.drop_index(op.f("ix_usage_events_provider"), table_name="usage_events")
    op.drop_index(op.f("ix_usage_events_user_id"), table_name="usage_events")
    op.drop_index(op.f("ix_usage_events_channel_id"), table_name="usage_events")
    op.drop_index(op.f("ix_usage_events_tenant_id"), table_name="usage_events")
    op.drop_table("usage_events")

    op.drop_index(op.f("ix_channels_channel_username"), table_name="channels")
    op.drop_index(op.f("ix_channels_tenant_id"), table_name="channels")
    op.drop_table("channels")

    op.drop_index(op.f("ix_memberships_user_id"), table_name="memberships")
    op.drop_index(op.f("ix_memberships_tenant_id"), table_name="memberships")
    op.drop_table("memberships")

    op.drop_index(op.f("ix_tenants_owner_user_id"), table_name="tenants")
    op.drop_table("tenants")

    # Drop enums
    sa.Enum(name="usageeventstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="membershiprole").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="tenantstatus").drop(op.get_bind(), checkfirst=True)
