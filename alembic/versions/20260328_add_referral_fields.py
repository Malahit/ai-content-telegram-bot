"""add referral fields to users table

Revision ID: add_referral_fields
Revises: add_topic_subscriptions
Create Date: 2026-03-28 14:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = "add_referral_fields"
down_revision: Union[str, None] = "add_topic_subscriptions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(conn, table, column):
    insp = inspect(conn)
    return column in [c['name'] for c in insp.get_columns(table)]


def _index_exists(conn, table, index_name):
    insp = inspect(conn)
    return any(ix['name'] == index_name for ix in insp.get_indexes(table))


def upgrade() -> None:
    bind = op.get_bind()

    if not _column_exists(bind, 'users', 'referral_code'):
        op.add_column("users", sa.Column("referral_code", sa.String(20), nullable=True))

    if not _column_exists(bind, 'users', 'referred_by'):
        op.add_column("users", sa.Column("referred_by", sa.BigInteger(), nullable=True))

    if not _column_exists(bind, 'users', 'referral_bonus_posts'):
        op.add_column(
            "users",
            sa.Column("referral_bonus_posts", sa.Integer(), nullable=False, server_default="0"),
        )

    if not _column_exists(bind, 'users', 'referrals_count'):
        op.add_column(
            "users",
            sa.Column("referrals_count", sa.Integer(), nullable=False, server_default="0"),
        )

    if not _index_exists(bind, 'users', 'ix_users_referral_code'):
        op.create_index("ix_users_referral_code", "users", ["referral_code"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_referral_code", table_name="users")
    op.drop_column("users", "referrals_count")
    op.drop_column("users", "referral_bonus_posts")
    op.drop_column("users", "referred_by")
    op.drop_column("users", "referral_code")
