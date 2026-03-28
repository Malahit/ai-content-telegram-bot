"""add topic_subscriptions table

Revision ID: add_topic_subscriptions
Revises: saas_multitenant_usage
Create Date: 2026-03-28 10:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "add_topic_subscriptions"
down_revision: Union[str, None] = "saas_multitenant_usage"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "topic_subscriptions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("topic", sa.String(500), nullable=False),
        sa.Column("send_hour_utc", sa.Integer(), nullable=False, server_default="8"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("last_sent_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_topic_subscriptions_telegram_id",
        "topic_subscriptions",
        ["telegram_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_topic_subscriptions_telegram_id", table_name="topic_subscriptions")
    op.drop_table("topic_subscriptions")
