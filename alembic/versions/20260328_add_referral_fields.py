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
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS referral_code VARCHAR(20)")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS referred_by BIGINT")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS referral_bonus_posts INTEGER NOT NULL DEFAULT 0")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS referrals_count INTEGER NOT NULL DEFAULT 0")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_referral_code ON users (referral_code)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_users_referral_code")
    op.drop_column("users", "referrals_count")
    op.drop_column("users", "referral_bonus_posts")
    op.drop_column("users", "referred_by")
    op.drop_column("users", "referral_code")
