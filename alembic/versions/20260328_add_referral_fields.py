"""add referral fields to users table

Revision ID: add_referral_fields
Revises: add_topic_subscriptions
Create Date: 2026-03-28 14:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "add_referral_fields"
down_revision: Union[str, None] = "add_topic_subscriptions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("referral_code", sa.String(20), nullable=True))
    op.add_column("users", sa.Column("referred_by", sa.BigInteger(), nullable=True))
    op.add_column(
        "users",
        sa.Column("referral_bonus_posts", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "users",
        sa.Column("referrals_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_users_referral_code", "users", ["referral_code"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_referral_code", table_name="users")
    op.drop_column("users", "referrals_count")
    op.drop_column("users", "referral_bonus_posts")
    op.drop_column("users", "referred_by")
    op.drop_column("users", "referral_code")
