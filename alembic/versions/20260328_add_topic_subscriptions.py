"""add topic_subscriptions table

Revision ID: a1b2c3d4e5f6
Revises:
Create Date: 2026-03-28
"""
from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        "topic_subscriptions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("topic", sa.String(500), nullable=False),
        sa.Column("send_hour_utc", sa.Integer(), nullable=False, server_default="8"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("last_sent_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_topic_subscriptions_telegram_id",
        "topic_subscriptions",
        ["telegram_id"],
    )


def downgrade():
    op.drop_index("ix_topic_subscriptions_telegram_id", table_name="topic_subscriptions")
    op.drop_table("topic_subscriptions")
