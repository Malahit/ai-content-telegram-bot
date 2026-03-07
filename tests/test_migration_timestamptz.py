"""
Tests for the convert_usage_events_timestamps_to_timestamptz Alembic migration.

Covers:
- SQLite no-op: upgrade() and downgrade() must not crash on SQLite.
- Helper _find_table_and_column() returns None on empty SQLite DB.
- Helper _find_table_and_column() returns correct (table, col) when table exists on SQLite.
- Helper _column_is_timestamptz() returns False for plain TIMESTAMP on SQLite.
- Source code does NOT contain 'information_schema' (regression guard).
- upgrade()/downgrade() contain the PostgreSQL dialect guard.
"""

import importlib.util
import os
import unittest

import sqlalchemy as sa

# ---------------------------------------------------------------------------
# Load the migration module without triggering Alembic bootstrap
# ---------------------------------------------------------------------------

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_MIGRATION_PATH = os.path.join(
    _ROOT,
    "alembic",
    "versions",
    "convert_usage_events_timestamps_to_timestamptz.py",
)


def _load_migration():
    spec = importlib.util.spec_from_file_location("timestamptz_migration", _MIGRATION_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_migration = _load_migration()


# ---------------------------------------------------------------------------
# SQLite fixture helpers
# ---------------------------------------------------------------------------

def _sqlite_conn():
    """Return an open SQLAlchemy connection to an in-memory SQLite database."""
    engine = sa.create_engine("sqlite:///:memory:")
    return engine.connect()


def _create_usage_events_table(conn, table_name="usage_events", col_name="created_at"):
    """Create a minimal usage-events table in *conn*."""
    conn.execute(
        sa.text(
            f'CREATE TABLE "{table_name}" '
            f'("{col_name}" DATETIME, "user_id" INTEGER)'
        )
    )
    conn.commit()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestMigrationSource(unittest.TestCase):
    """Static source-code checks (no DB required)."""

    def setUp(self):
        with open(_MIGRATION_PATH) as fh:
            self.source = fh.read()

    def test_no_information_schema_queries(self):
        """Migration must not execute information_schema SQL queries."""
        # Allow the word in comments/docstrings, but not in SQL string literals.
        # We check that 'FROM information_schema' never appears in the source.
        self.assertNotIn(
            "FROM information_schema",
            self.source,
            "Migration must not query information_schema (PostgreSQL-only); "
            "use sa.inspect() instead.",
        )

    def test_uses_sa_inspect(self):
        """Migration must use sa.inspect() for dialect-agnostic discovery."""
        self.assertIn(
            "sa.inspect(",
            self.source,
            "Migration must use sa.inspect() for dialect-agnostic table/column discovery.",
        )

    def test_postgresql_dialect_guard_in_upgrade(self):
        """upgrade() must guard PostgreSQL-specific code with a dialect check."""
        self.assertIn(
            'conn.dialect.name != "postgresql"',
            self.source,
        )

    def test_revision_metadata(self):
        self.assertEqual(_migration.revision, "convert_usage_events_timestamptz")
        self.assertEqual(_migration.down_revision, "saas_multitenant_usage")


class TestFindTableAndColumnSQLite(unittest.TestCase):
    """_find_table_and_column() must work on SQLite using sa.inspect()."""

    def test_returns_none_when_no_tables(self):
        """Returns None on an empty SQLite database."""
        conn = _sqlite_conn()
        result = _migration._find_table_and_column(conn)
        self.assertIsNone(result)
        conn.close()

    def test_finds_usage_events_created_at(self):
        """Detects the standard (usage_events, created_at) pair."""
        conn = _sqlite_conn()
        _create_usage_events_table(conn, "usage_events", "created_at")
        result = _migration._find_table_and_column(conn)
        self.assertEqual(result, ("usage_events", "created_at"))
        conn.close()

    def test_finds_usage_events_createdat(self):
        """Detects the legacy column name 'createdat' in 'usage_events'."""
        conn = _sqlite_conn()
        _create_usage_events_table(conn, "usage_events", "createdat")
        result = _migration._find_table_and_column(conn)
        self.assertEqual(result, ("usage_events", "createdat"))
        conn.close()

    def test_finds_usageevents_created_at(self):
        """Detects the legacy table 'usageevents' with 'created_at'."""
        conn = _sqlite_conn()
        _create_usage_events_table(conn, "usageevents", "created_at")
        result = _migration._find_table_and_column(conn)
        self.assertEqual(result, ("usageevents", "created_at"))
        conn.close()

    def test_finds_usageevents_createdat(self):
        """Detects fully-legacy (usageevents, createdat) pair."""
        conn = _sqlite_conn()
        _create_usage_events_table(conn, "usageevents", "createdat")
        result = _migration._find_table_and_column(conn)
        self.assertEqual(result, ("usageevents", "createdat"))
        conn.close()

    def test_prefers_usage_events_over_usageevents(self):
        """Prefers 'usage_events' over 'usageevents' when both exist."""
        conn = _sqlite_conn()
        _create_usage_events_table(conn, "usage_events", "created_at")
        _create_usage_events_table(conn, "usageevents", "created_at")
        result = _migration._find_table_and_column(conn)
        self.assertEqual(result[0], "usage_events")
        conn.close()

    def test_returns_none_when_unrelated_table(self):
        """Returns None when only unrelated tables exist."""
        conn = _sqlite_conn()
        conn.execute(sa.text("CREATE TABLE users (id INTEGER)"))
        conn.commit()
        result = _migration._find_table_and_column(conn)
        self.assertIsNone(result)
        conn.close()


class TestColumnIsTimestamptzSQLite(unittest.TestCase):
    """_column_is_timestamptz() on SQLite (always False for plain DATETIME)."""

    def test_plain_datetime_is_not_timestamptz(self):
        """DATETIME columns on SQLite are not TIMESTAMPTZ."""
        conn = _sqlite_conn()
        _create_usage_events_table(conn, "usage_events", "created_at")
        result = _migration._column_is_timestamptz(conn, "usage_events", "created_at")
        self.assertFalse(result)
        conn.close()

    def test_missing_column_returns_false(self):
        """Returns False when the column does not exist."""
        conn = _sqlite_conn()
        _create_usage_events_table(conn, "usage_events", "created_at")
        result = _migration._column_is_timestamptz(conn, "usage_events", "nonexistent_col")
        self.assertFalse(result)
        conn.close()


class TestUpgradeDowngradeSQLiteNoop(unittest.TestCase):
    """
    upgrade() and downgrade() must be silent no-ops on SQLite.

    We cannot call op.get_bind() in a unit test (it requires a live Alembic
    migration context), so we patch it to return a real SQLite connection and
    verify the functions complete without raising.
    """

    def _run_with_sqlite_conn(self, fn, setup=None):
        """Execute *fn* with op.get_bind() patched to a SQLite connection.

        *setup* is an optional callable that receives the connection and may
        perform pre-migration table creation (e.g. CREATE TABLE).
        """
        conn = _sqlite_conn()
        if setup is not None:
            setup(conn)
        original_get_bind = _migration.op.get_bind
        try:
            _migration.op.get_bind = lambda: conn
            fn()  # must not raise
        finally:
            _migration.op.get_bind = original_get_bind
            conn.close()

    def test_upgrade_noop_on_empty_sqlite(self):
        """upgrade() must not crash on an empty SQLite database."""
        self._run_with_sqlite_conn(_migration.upgrade)

    def test_downgrade_noop_on_empty_sqlite(self):
        """downgrade() must not crash on an empty SQLite database."""
        self._run_with_sqlite_conn(_migration.downgrade)

    def test_upgrade_noop_with_usage_events_table_on_sqlite(self):
        """upgrade() must not crash even when usage_events table exists on SQLite."""
        def _setup(conn):
            _create_usage_events_table(conn, "usage_events", "created_at")

        self._run_with_sqlite_conn(_migration.upgrade, setup=_setup)

    def test_downgrade_noop_with_usage_events_table_on_sqlite(self):
        """downgrade() must not crash even when usage_events table exists on SQLite."""
        def _setup(conn):
            _create_usage_events_table(conn, "usage_events", "created_at")

        self._run_with_sqlite_conn(_migration.downgrade, setup=_setup)


if __name__ == "__main__":
    unittest.main()
