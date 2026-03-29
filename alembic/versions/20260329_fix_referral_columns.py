"""force add referral columns if missing (hotfix)

Revision ID: fix_referral_columns
Revises: merge_all_heads
Create Date: 2026-03-29 06:00:00.000000

This migration is a safety net: adds referral columns using
ALTER TABLE ... IF NOT EXISTS (idempotent on PostgreSQL).
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision: str = "fix_referral_columns"
down_revision: Union[str, None] = "merge_all_heads"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    bind.execute(sa.text(
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS referral_code VARCHAR(20) DEFAULT NULL"
    ))
    bind.execute(sa.text(
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS referred_by BIGINT DEFAULT NULL"
    ))
    bind.execute(sa.text(
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS referral_bonus_posts INTEGER NOT NULL DEFAULT 0"
    ))
    bind.execute(sa.text(
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS referrals_count INTEGER NOT NULL DEFAULT 0"
    ))

    bind.execute(sa.text(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_users_referral_code ON users (referral_code)"
    ))


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("DROP INDEX IF EXISTS ix_users_referral_code"))
    bind.execute(sa.text("ALTER TABLE users DROP COLUMN IF EXISTS referrals_count"))
    bind.execute(sa.text("ALTER TABLE users DROP COLUMN IF EXISTS referral_bonus_posts"))
    bind.execute(sa.text("ALTER TABLE users DROP COLUMN IF EXISTS referred_by"))
    bind.execute(sa.text("ALTER TABLE users DROP COLUMN IF EXISTS referral_code"))
