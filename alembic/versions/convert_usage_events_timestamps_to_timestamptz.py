"""Convert usage_events/usageevents created_at/createdat to TIMESTAMP WITH TIME ZONE

Revision ID: convert_usage_events_timestamptz
Revises: saas_multitenant_usage
Create Date: 2026-03-01 00:00:00.000000

This migration detects the actual table and column names present in the database
(handling both 'usage_events'/'usageevents' and 'created_at'/'createdat' variants)
and converts the timestamp column to TIMESTAMPTZ, treating existing naive values as UTC.

Uses SQLAlchemy Inspector for dialect-agnostic table/column discovery (works on
both SQLite and PostgreSQL).  The actual ALTER TABLE is PostgreSQL-only and is
guarded by a dialect check; all other databases receive a silent no-op.

"""

from typing import Sequence, Union, Optional, Tuple

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "convert_usage_events_timestamptz"
down_revision: Union[str, None] = "saas_multitenant_usage"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _find_table_and_column(conn) -> Optional[Tuple[str, str]]:
    """
    Detect which usage-events table and timestamp column exist in this database.

    Uses SQLAlchemy Inspector so it works on SQLite as well as PostgreSQL.

    Checks for (in priority order):
      1. usage_events / created_at  (new standard naming)
      2. usage_events / createdat   (new table, legacy column)
      3. usageevents  / created_at  (legacy table, new column)
      4. usageevents  / createdat   (fully legacy – seen in production logs)

    Returns (table_name, column_name) for the first match, or None if not found.
    """
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())
    for table_name in ("usage_events", "usageevents"):
        if table_name not in existing_tables:
            continue
        col_names = {c["name"] for c in inspector.get_columns(table_name)}
        for col_name in ("created_at", "createdat"):
            if col_name in col_names:
                return (table_name, col_name)
    return None


def _column_is_timestamptz(conn, table_name: str, col_name: str) -> bool:
    """
    Return True if *col_name* in *table_name* is already TIMESTAMP WITH TIME ZONE.

    Uses SQLAlchemy Inspector column type metadata so it works on any dialect.
    Falls back to a string match for dialects that do not expose a ``timezone``
    attribute on their type objects.
    """
    inspector = sa.inspect(conn)
    for col in inspector.get_columns(table_name):
        if col["name"] != col_name:
            continue
        col_type = col["type"]
        # Primary check: SQLAlchemy sets .timezone = True for TIMESTAMPTZ columns.
        if hasattr(col_type, "timezone") and col_type.timezone:
            return True
        # Fallback: string representation for dialects that don't expose .timezone.
        type_str = str(col_type).upper()
        if "TIME ZONE" in type_str or "TIMESTAMPTZ" in type_str:
            return True
        return False
    return False


def upgrade() -> None:
    """
    Convert the usage-events timestamp column from naive TIMESTAMP to TIMESTAMPTZ.

    Works regardless of whether the table is named 'usage_events' or 'usageevents'
    and whether the column is 'created_at' or 'createdat'.
    Existing values are assumed to be UTC and are cast with AT TIME ZONE 'UTC'.

    No-op on non-PostgreSQL databases (e.g. SQLite): TIMESTAMPTZ conversion is
    a PostgreSQL-specific operation.
    """
    conn = op.get_bind()
    # TIMESTAMPTZ ALTER TABLE is PostgreSQL-only; skip on all other dialects.
    if conn.dialect.name != "postgresql":
        return
    found = _find_table_and_column(conn)
    if found is None:
        # Table does not exist yet (fresh DB); nothing to convert.
        return

    table_name, col_name = found

    if _column_is_timestamptz(conn, table_name, col_name):
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

    No-op on non-PostgreSQL databases.
    """
    conn = op.get_bind()
    # TIMESTAMPTZ ALTER TABLE is PostgreSQL-only; skip on all other dialects.
    if conn.dialect.name != "postgresql":
        return
    found = _find_table_and_column(conn)
    if found is None:
        return

    table_name, col_name = found

    if not _column_is_timestamptz(conn, table_name, col_name):
        # Already naive TIMESTAMP – nothing to revert.
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
