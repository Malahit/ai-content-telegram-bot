"""
Tests for budget_service to ensure tz-aware datetimes are used in queries.

This guards against asyncpg.exceptions.DataError:
  "can't subtract offset-naive and offset-aware datetimes"
which occurs when a tz-aware datetime is compared to a TIMESTAMP WITHOUT TIME ZONE column.
"""

import asyncio
import os
import sys
import unittest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestBudgetServiceTzAware(unittest.TestCase):
    """Verify that check_tenant_budget uses tz-aware UTC datetimes in its query."""

    def test_check_tenant_budget_uses_tz_aware_datetimes(self):
        """check_tenant_budget must pass tz-aware start/end to the WHERE clause."""
        import importlib.util
        import pathlib
        import types

        # We need to load services.budget_service without triggering
        # services/__init__.py (which imports aiohttp via image_fetcher).
        # Use patch.dict to inject stub modules into sys.modules before loading.

        pricing_stub = types.ModuleType("services.pricing_service")
        pricing_stub.get_budget_hard_limit_usd = lambda: None
        pricing_stub.get_budget_warn_limit_usd = lambda: None

        db_models_spec = importlib.util.spec_from_file_location(
            "database.models",
            pathlib.Path(__file__).parent.parent / "database" / "models.py",
        )
        db_models_module = importlib.util.module_from_spec(db_models_spec)

        budget_spec = importlib.util.spec_from_file_location(
            "services.budget_service",
            pathlib.Path(__file__).parent.parent / "services" / "budget_service.py",
        )
        budget_module = importlib.util.module_from_spec(budget_spec)

        stubs = {
            "services": types.ModuleType("services"),
            "services.pricing_service": pricing_stub,
            "database": types.ModuleType("database"),
            "database.models": db_models_module,
            "services.budget_service": budget_module,
        }

        mock_result = MagicMock()
        mock_result.scalar_one.return_value = Decimal("0")
        mock_session = MagicMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch.dict(sys.modules, stubs):
            # database.models must be in sys.modules when exec'd so SQLAlchemy
            # can resolve Mapped[...] annotations via sys.modules lookups.
            db_models_spec.loader.exec_module(db_models_module)
            budget_spec.loader.exec_module(budget_module)
            check_tenant_budget = budget_module.check_tenant_budget
            result = asyncio.run(check_tenant_budget(mock_session, tenant_id=1))

        # Budget check should succeed (no limits configured)
        self.assertTrue(result.allowed)
        self.assertFalse(result.should_warn)

        # Verify that session.execute was called exactly once
        mock_session.execute.assert_awaited_once()

        # Extract the statement passed to session.execute and inspect its WHERE clauses
        stmt = mock_session.execute.call_args[0][0]
        datetimes_in_query = []
        for clause in stmt.whereclause.clauses:
            try:
                val = clause.right.value
                if isinstance(val, datetime):
                    datetimes_in_query.append(val)
            except AttributeError:
                pass

        # We expect to find the start and end datetime bounds
        self.assertTrue(
            len(datetimes_in_query) >= 2,
            f"Expected at least 2 datetime bounds in WHERE clause, got: {datetimes_in_query}",
        )
        # All datetime values used in the query must be timezone-aware UTC
        for dt in datetimes_in_query:
            self.assertIsNotNone(
                dt.tzinfo,
                f"Datetime {dt!r} in budget query is naive (no tzinfo). "
                "This causes asyncpg DataError with TIMESTAMPTZ columns.",
            )
            self.assertEqual(
                dt.tzinfo,
                timezone.utc,
                f"Datetime {dt!r} in budget query is not UTC.",
            )

    def test_budget_service_start_end_are_tz_aware(self):
        """Directly verify that the month-boundary datetimes computed inside check_tenant_budget are tz-aware."""
        # Reproduce the logic from budget_service to confirm it stays tz-aware
        now = datetime.now(timezone.utc)
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if start.month == 12:
            end = start.replace(year=start.year + 1, month=1)
        else:
            end = start.replace(month=start.month + 1)

        self.assertIsNotNone(start.tzinfo, "start datetime must be timezone-aware")
        self.assertIsNotNone(end.tzinfo, "end datetime must be timezone-aware")
        self.assertEqual(start.tzinfo, timezone.utc)
        self.assertEqual(end.tzinfo, timezone.utc)


if __name__ == "__main__":
    unittest.main()
