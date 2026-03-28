"""Merge all heads into single head

Revision ID: merge_all_heads
Revises: add_autopost_subscriptions, add_referral_fields, convert_usage_events_timestamptz
Create Date: 2026-03-29 00:00:00.000000

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "merge_all_heads"
down_revision: Union[str, Sequence[str], None] = (
    "add_autopost_subscriptions",
    "add_referral_fields",
    "convert_usage_events_timestamptz",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
