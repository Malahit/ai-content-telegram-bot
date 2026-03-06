"""
Structural regression tests for the Alembic migration configuration.

Covers:
- PR #1 regression: alembic/env.py must override ``sqlalchemy.url`` from the
  ``DATABASE_URL`` environment variable so that Railway (and any production
  environment) uses a PostgreSQL URL rather than the SQLite fallback in
  alembic.ini.

Uses AST and source-text inspection to avoid running the full Alembic
bootstrap (which requires a live database connection) during tests.
"""

import ast
import os
import sys
import unittest

# Make sure the project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ENV_PY = os.path.join(_ROOT, "alembic", "env.py")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_env() -> ast.Module:
    with open(_ENV_PY) as fh:
        return ast.parse(fh.read(), filename="alembic/env.py")


def _read_env() -> str:
    with open(_ENV_PY) as fh:
        return fh.read()


def _has_import_from(tree: ast.Module, module: str, name: str) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == module:
            if any(alias.name == name for alias in node.names):
                return True
    return False


def _top_level_function_names(tree: ast.Module) -> set:
    return {
        node.name
        for node in ast.iter_child_nodes(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestAlembicEnvConfig(unittest.TestCase):
    """
    PR #1 regression: alembic/env.py must override ``sqlalchemy.url`` from the
    ``DATABASE_URL`` environment variable.

    Without this override, Alembic falls back to the SQLite URL in
    alembic.ini, which means migrations would silently run against the wrong
    database in production (Railway PostgreSQL).
    """

    def setUp(self):
        self.source = _read_env()
        self.tree = _parse_env()

    # --- DATABASE_URL override (the most critical production safety check) ---

    def test_reads_database_url_env_var(self):
        """env.py must read the DATABASE_URL environment variable."""
        self.assertIn(
            "DATABASE_URL",
            self.source,
            "alembic/env.py must reference the DATABASE_URL environment variable",
        )

    def test_overrides_sqlalchemy_url(self):
        """env.py must call set_main_option('sqlalchemy.url', ...) to override the ini value."""
        self.assertIn(
            "set_main_option",
            self.source,
            "alembic/env.py must call config.set_main_option() to override sqlalchemy.url",
        )
        self.assertIn(
            "sqlalchemy.url",
            self.source,
            "alembic/env.py must reference 'sqlalchemy.url' as the setting to override",
        )

    def test_database_url_override_is_conditional(self):
        """The override must be conditional on DATABASE_URL being set (not unconditional)."""
        # Verify a conditional branch exists (if _db_url: ...)
        # This guards against accidentally always overriding with an empty string.
        found_conditional = False
        for node in ast.walk(self.tree):
            if isinstance(node, ast.If):
                # Check that the condition involves the DATABASE_URL variable
                cond_src = ast.unparse(node.test)
                if "db_url" in cond_src or "DATABASE_URL" in cond_src:
                    found_conditional = True
                    break
        self.assertTrue(
            found_conditional,
            "alembic/env.py must conditionally override sqlalchemy.url only when DATABASE_URL is set",
        )

    def test_warning_emitted_when_database_url_absent(self):
        """env.py must log a warning when DATABASE_URL is not set."""
        self.assertIn(
            "DATABASE_URL is not set",
            self.source,
            "alembic/env.py must warn operators when DATABASE_URL is missing",
        )

    # --- Model metadata (required for autogenerate support) ---

    def test_imports_base_from_database_models(self):
        """env.py must import Base from database.models for autogenerate support."""
        self.assertTrue(
            _has_import_from(self.tree, "database.models", "Base"),
            "alembic/env.py must contain `from database.models import Base`",
        )

    def test_sets_target_metadata(self):
        """env.py must set target_metadata so autogenerate can detect schema changes."""
        self.assertIn(
            "target_metadata",
            self.source,
            "alembic/env.py must assign target_metadata for autogenerate support",
        )

    # --- Migration runner functions ---

    def test_defines_run_migrations_offline(self):
        """env.py must define run_migrations_offline()."""
        self.assertIn(
            "run_migrations_offline",
            _top_level_function_names(self.tree),
            "alembic/env.py must define run_migrations_offline()",
        )

    def test_defines_run_migrations_online(self):
        """env.py must define run_migrations_online()."""
        self.assertIn(
            "run_migrations_online",
            _top_level_function_names(self.tree),
            "alembic/env.py must define run_migrations_online()",
        )

    def test_migration_mode_dispatch(self):
        """env.py must call either offline or online runner based on context.is_offline_mode()."""
        self.assertIn(
            "is_offline_mode",
            self.source,
            "alembic/env.py must dispatch to offline/online runner via context.is_offline_mode()",
        )

    # --- No syntax errors ---

    def test_parses_without_syntax_errors(self):
        """alembic/env.py must contain valid Python syntax."""
        # If _parse_env() failed we wouldn't reach setUp, but this makes the
        # intent explicit and produces a clearer failure message.
        try:
            ast.parse(self.source)
        except SyntaxError as exc:
            self.fail(f"alembic/env.py has a syntax error: {exc}")


if __name__ == "__main__":
    unittest.main()
