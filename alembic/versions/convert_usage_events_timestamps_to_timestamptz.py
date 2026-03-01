"""Convert usage_events/usageevents created_at/createdat to TIMESTAMP WITH TIME ZONE

Revision ID: convert_usage_events_timestamptz
Revises: saas_multitenant_usage
Create Date: 2026-03-01 00:00:00.000000

This migration detects the actual table and column names present in the database
(handling both 'usage_events'/'usageevents' and 'created_at'/'createdat' variants)
and converts the timestamp column to TIMESTAMPTZ, treating existing naive values as UTC.

"""

from typing import Sequence, Union, Optional, Tuple

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "convert_usage_events_timestamptz"
down_revision: Union[str, None] = "saas_multitenant_usage"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Exhaustive allow-lists guard against unexpected values from information_schema.
_ALLOWED_TABLES = frozenset({"usage_events", "usageevents"})
_ALLOWED_COLUMNS = frozenset({"created_at", "createdat"})


def _find_table_and_column(conn) -> Optional[Tuple[str, str]]:
    """
    Detect which usage-events table and timestamp column exist in this database.

    Checks for (in priority order):
      1. usage_events / created_at  (new standard naming)
      2. usage_events / createdat   (new table, legacy column)
      3. usageevents  / created_at  (legacy table, new column)
      4. usageevents  / createdat   (fully legacy – seen in production logs)

    Returns (table_name, column_name) for the first match, or None if not found.
    """
    result = conn.execute(
        sa.text(
            """
            SELECT table_name, column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name   IN ('usage_events', 'usageevents')
              AND column_name  IN ('created_at', 'createdat')
            ORDER BY
              CASE table_name  WHEN 'usage_events' THEN 1 ELSE 2 END,
              CASE column_name WHEN 'created_at'   THEN 1 ELSE 2 END
            LIMIT 1
            """
        )
    )
    row = result.fetchone()
    if row is None:
        return None
    table_name, col_name = row[0], row[1]
    # Validate against the allow-list before using in dynamic SQL.
    if table_name not in _ALLOWED_TABLES or col_name not in _ALLOWED_COLUMNS:
        raise ValueError(
            f"Unexpected table/column from information_schema: {table_name!r}.{col_name!r}"
        )
    return (table_name, col_name)


def _column_data_type(conn, table_name: str, col_name: str) -> Optional[str]:
    """Return the information_schema data_type string for a column, or None."""
    result = conn.execute(
        sa.text(
            """
            SELECT data_type
            FROM information_schema.columns
            WHERE table_schema = current_schema()
              AND table_name   = :tbl
              AND column_name  = :col
            """
        ),
        {"tbl": table_name, "col": col_name},
    )
    row = result.fetchone()
    return row[0] if row else None


def upgrade() -> None:
    """
    Convert the usage-events timestamp column from naive TIMESTAMP to TIMESTAMPTZ.

    Works regardless of whether the table is named 'usage_events' or 'usageevents'
    and whether the column is 'created_at' or 'createdat'.
    Existing values are assumed to be UTC and are cast with AT TIME ZONE 'UTC'.
    """
    conn = op.get_bind()
    found = _find_table_and_column(conn)
    if found is None:
        # Table does not exist yet (fresh DB); nothing to convert.
        return

    table_name, col_name = found

    current_type = _column_data_type(conn, table_name, col_name)
    if current_type == "timestamp with time zone":
        # Already TIMESTAMPTZ – idempotent, nothing to do.
        return

    idx_name = f"ix_{table_name}_{col_name}"

    # Drop the index before changing the column type (Postgres requirement).
    conn.execute(sa.text(f'DROP INDEX IF EXISTS "{idx_name}"'))

    # Alter column: naive TIMESTAMP → TIMESTAMPTZ, treating old values as UTC.
    conn.execute(
        sa.text(
            f'ALTER TABLE "{table_name}" '
            f'ALTER COLUMN "{col_name}" '
            f"TYPE TIMESTAMP WITH TIME ZONE "
            f'USING "{col_name}" AT TIME ZONE \'UTC\''
        )
    )

    # Recreate the index.
    conn.execute(
        sa.text(f'CREATE INDEX IF NOT EXISTS "{idx_name}" ON "{table_name}" ("{col_name}")')
    )


def downgrade() -> None:
    """
    Revert the usage-events timestamp column from TIMESTAMPTZ back to naive TIMESTAMP.

    Values are converted from UTC-aware back to naive UTC using AT TIME ZONE 'UTC'.
    """
    conn = op.get_bind()
    found = _find_table_and_column(conn)
    if found is None:
        return

    table_name, col_name = found

    current_type = _column_data_type(conn, table_name, col_name)
    if current_type != "timestamp with time zone":
        # Already naive – nothing to revert.
        return

    idx_name = f"ix_{table_name}_{col_name}"

    conn.execute(sa.text(f'DROP INDEX IF EXISTS "{idx_name}"'))

    conn.execute(
        sa.text(
            f'ALTER TABLE "{table_name}" '
            f'ALTER COLUMN "{col_name}" '
            f"TYPE TIMESTAMP WITHOUT TIME ZONE "
            f'USING "{col_name}" AT TIME ZONE \'UTC\''
        )
    )

    conn.execute(
        sa.text(f'CREATE INDEX IF NOT EXISTS "{idx_name}" ON "{table_name}" ("{col_name}")')
    )
