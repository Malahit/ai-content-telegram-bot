"""add user_bot_token to autopost_subscriptions

Revision ID: add_user_bot_token
Revises: merge_all_heads
Create Date: 2026-03-30 00:00:00.000000

"""

from typing import Sequence, Union
from alembic import op

revision: str = "add_user_bot_token"
down_revision: Union[str, None] = "merge_all_heads"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE autopost_subscriptions "
        "ADD COLUMN IF NOT EXISTS user_bot_token VARCHAR(120)"
    )


def downgrade() -> None:
    op.drop_column("autopost_subscriptions", "user_bot_token")
