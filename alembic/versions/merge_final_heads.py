"""Merge final heads: add_user_bot_token + saas_multitenant_usage

Revision ID: merge_final_heads
Revises: add_user_bot_token, saas_multitenant_usage
Create Date: 2026-04-05 00:00:00.000000

Why this file exists
--------------------
The previous merge_all_heads.py did not include the saas_multitenant_usage
branch, so Alembic detected two independent head revisions and refused to
run ``alembic upgrade head``.  This no-op merge revision makes the history
linear again.
"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "merge_final_heads"
down_revision: Union[str, Sequence[str], None] = (
    "add_user_bot_token",
    "saas_multitenant_usage",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
