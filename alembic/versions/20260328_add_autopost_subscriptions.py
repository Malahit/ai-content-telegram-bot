"""add autopost_subscriptions table

Revision ID: add_autopost_subscriptions
Revises: add_topic_subscriptions
Create Date: 2026-03-28 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "add_autopost_subscriptions"
down_revision: Union[str, None] = "add_topic_subscriptions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "autopost_subscriptions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("channel_id", sa.String(100), nullable=False),
        sa.Column("channel_title", sa.String(255), nullable=True),
        sa.Column("topic", sa.String(500), nullable=False),
        sa.Column("frequency", sa.String(50), nullable=False),
        sa.Column("send_hour_utc", sa.Integer(), nullable=False),
        sa.Column("send_hour_local", sa.Integer(), nullable=False),
        sa.Column("timezone", sa.String(50), nullable=False, server_default="Europe/Moscow"),
        sa.Column("plan_type", sa.String(20), nullable=False),
        sa.Column("stars_paid", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("telegram_charge_id", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "starts_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_post_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("posts_generated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_autopost_subscriptions_telegram_id",
        "autopost_subscriptions",
        ["telegram_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_autopost_subscriptions_telegram_id", table_name="autopost_subscriptions")
    op.drop_table("autopost_subscriptions")
