"""Convert usage_events.created_at to TIMESTAMP WITH TIME ZONE

Revision ID: convert_usage_events_timestamptz
Revises: saas_multitenant_usage
Create Date: 2026-03-01 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "convert_usage_events_timestamptz"
down_revision: Union[str, None] = "saas_multitenant_usage"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Convert usage_events.created_at from TIMESTAMP (naive) to TIMESTAMPTZ.
    # Existing values are assumed to be in UTC and are converted accordingly.
    op.alter_column(
        "usage_events",
        "created_at",
        type_=sa.DateTime(timezone=True),
        postgresql_using="created_at AT TIME ZONE 'UTC'",
        existing_type=sa.DateTime(),
        existing_nullable=False,
        existing_server_default=sa.text("CURRENT_TIMESTAMP"),
    )


def downgrade() -> None:
    # Revert usage_events.created_at back to TIMESTAMP WITHOUT TIME ZONE.
    # Values are cast back to naive UTC.
    op.alter_column(
        "usage_events",
        "created_at",
        type_=sa.DateTime(),
        postgresql_using="created_at AT TIME ZONE 'UTC'",
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=False,
        existing_server_default=sa.text("CURRENT_TIMESTAMP"),
    )
