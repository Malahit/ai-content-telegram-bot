"""
Structural regression tests for the runtime entrypoint and package imports.

Covers critical paths touched by previous PRs:
- PR #2 (entrypoint unification): main.py must delegate to bot.py; it must not
  contain its own handler logic.
- PR #3 (structure cleanup): handlers and middlewares packages must export the
  expected names so the rest of the codebase can import them correctly.
- PR #112 (subscription middleware wiring): bot.py must import and register
  SubscriptionMiddleware on the dispatcher.

AST-based checks are used for bot.py and main.py to avoid triggering
module-level side-effects (Bot instantiation, env-var loading) during test
collection.  Direct imports are used for the package __init__ modules
because those have no heavyweight side-effects.
"""

import ast
import os
import sys
import unittest

# Make sure the project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse(relative_path: str) -> ast.Module:
    """Read and parse a file relative to the project root."""
    full_path = os.path.join(_ROOT, relative_path)
    with open(full_path) as fh:
        return ast.parse(fh.read(), filename=relative_path)


def _read(relative_path: str) -> str:
    """Read source text of a file relative to the project root."""
    with open(os.path.join(_ROOT, relative_path)) as fh:
        return fh.read()


def _top_level_names(tree: ast.Module) -> set:
    """Return names of all top-level function/class definitions."""
    return {
        node.name
        for node in ast.iter_child_nodes(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    }


def _has_import_from(tree: ast.Module, module: str, name: str) -> bool:
    """Return True if ``from <module> import <name>`` appears anywhere in *tree*."""
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == module:
            if any(alias.name == name for alias in node.names):
                return True
    return False


# ---------------------------------------------------------------------------
# main.py entrypoint tests  (PR #2 regression)
# ---------------------------------------------------------------------------

class TestMainPyEntrypoint(unittest.TestCase):
    """
    PR #2 regression: main.py must be a thin wrapper that delegates to bot.py.

    If bot logic is accidentally added back to main.py, or the delegation is
    removed, these tests will catch it before it reaches production.
    """

    def setUp(self):
        self.tree = _parse("main.py")
        self.source = _read("main.py")

    def test_imports_main_from_bot(self):
        """main.py must contain ``from bot import main``."""
        self.assertTrue(
            _has_import_from(self.tree, "bot", "main"),
            "main.py must contain `from bot import main` to delegate to bot.py",
        )

    def test_calls_asyncio_run_main(self):
        """main.py must call ``asyncio.run(main())`` in its __main__ guard."""
        self.assertIn(
            "asyncio.run(main())",
            self.source,
            "main.py must call asyncio.run(main()) inside the __main__ guard",
        )

    def test_no_handler_definitions(self):
        """main.py must not define any top-level handlers or classes (thin wrapper only)."""
        top_level = _top_level_names(self.tree)
        self.assertEqual(
            top_level,
            set(),
            f"main.py should define no top-level functions/classes; found: {top_level}",
        )


# ---------------------------------------------------------------------------
# bot.py structure tests  (PR #2 + PR #112 regression)
# ---------------------------------------------------------------------------

class TestBotPyStructure(unittest.TestCase):
    """
    Structural regression tests for bot.py.

    Uses AST parsing to avoid importing bot.py (which would trigger Bot
    instantiation and require real env vars during test collection).
    """

    def setUp(self):
        self.tree = _parse("bot.py")
        self.source = _read("bot.py")
        self._funcs = _top_level_names(self.tree)

    def test_defines_main(self):
        """bot.py must define the async main() entry coroutine."""
        self.assertIn("main", self._funcs, "bot.py must define main()")

    def test_defines_on_startup(self):
        """bot.py must define on_startup() so the scheduler and DB are initialised."""
        self.assertIn("on_startup", self._funcs, "bot.py must define on_startup()")

    def test_defines_on_shutdown(self):
        """bot.py must define on_shutdown() for graceful resource cleanup."""
        self.assertIn("on_shutdown", self._funcs, "bot.py must define on_shutdown()")

    def test_defines_validate_bot_token(self):
        """bot.py must define _validate_bot_token() for fail-fast startup."""
        self.assertIn(
            "_validate_bot_token",
            self._funcs,
            "bot.py must define _validate_bot_token() for fail-fast token validation",
        )

    def test_imports_subscription_middleware(self):
        """PR #112 regression: bot.py must import SubscriptionMiddleware."""
        self.assertIn(
            "SubscriptionMiddleware",
            self.source,
            "bot.py must import SubscriptionMiddleware from middlewares",
        )

    def test_registers_subscription_middleware(self):
        """PR #112 regression: bot.py must register SubscriptionMiddleware on dp."""
        self.assertIn(
            "SubscriptionMiddleware(",
            self.source,
            "bot.py must instantiate SubscriptionMiddleware and register it on the dispatcher",
        )

    def test_includes_subscription_router(self):
        """bot.py must include the subscription router in the dispatcher."""
        self.assertIn(
            "subscription_router",
            self.source,
            "bot.py must include subscription_router via dp.include_router()",
        )

    def test_calls_config_validate_startup(self):
        """main() must call config.validate_startup() for early diagnostic logging."""
        self.assertIn(
            "config.validate_startup()",
            self.source,
            "bot.py main() must call config.validate_startup() before polling begins",
        )

    def test_on_startup_logs_health_summary(self):
        """on_startup() must emit a health summary so operators can confirm all components."""
        self.assertIn(
            "health summary",
            self.source.lower(),
            "on_startup() should log a health summary for production diagnostics",
        )


# ---------------------------------------------------------------------------
# handlers package tests  (PR #3 regression)
# ---------------------------------------------------------------------------

class TestHandlersPackage(unittest.TestCase):
    """
    PR #3 regression: the handlers package must export subscription_router.

    If the package __init__.py is accidentally emptied or the export name is
    changed, this test will catch it immediately.
    """

    def test_exports_subscription_router(self):
        """handlers package must export subscription_router."""
        from handlers import subscription_router  # noqa: F401
        self.assertIsNotNone(subscription_router)

    def test_all_declares_subscription_router(self):
        """handlers.__all__ must list subscription_router."""
        import handlers
        self.assertIn(
            "subscription_router",
            handlers.__all__,
            "handlers.__all__ must include 'subscription_router'",
        )

    def test_subscription_router_is_aiogram_router(self):
        """subscription_router must be an aiogram Router instance."""
        from handlers import subscription_router
        from aiogram import Router
        self.assertIsInstance(
            subscription_router,
            Router,
            "subscription_router must be an aiogram.Router",
        )


# ---------------------------------------------------------------------------
# middlewares package tests  (PR #112 regression)
# ---------------------------------------------------------------------------

class TestMiddlewaresPackage(unittest.TestCase):
    """
    PR #112 regression: the middlewares package must export SubscriptionMiddleware.
    """

    def test_exports_subscription_middleware(self):
        """middlewares package must export SubscriptionMiddleware."""
        from middlewares import SubscriptionMiddleware  # noqa: F401
        self.assertTrue(callable(SubscriptionMiddleware))

    def test_all_declares_subscription_middleware(self):
        """middlewares.__all__ must list SubscriptionMiddleware."""
        import middlewares
        self.assertIn(
            "SubscriptionMiddleware",
            middlewares.__all__,
            "middlewares.__all__ must include 'SubscriptionMiddleware'",
        )

    def test_subscription_middleware_accepts_empty_premium_list(self):
        """SubscriptionMiddleware(premium_commands=[]) must initialise (bot.py startup wiring)."""
        from middlewares import SubscriptionMiddleware
        mw = SubscriptionMiddleware(premium_commands=[])
        self.assertEqual(mw.premium_commands, [])

    def test_subscription_middleware_accepts_command_list(self):
        """SubscriptionMiddleware can be created with a non-empty premium command list."""
        from middlewares import SubscriptionMiddleware
        mw = SubscriptionMiddleware(premium_commands=["generate", "stats"])
        self.assertEqual(mw.premium_commands, ["generate", "stats"])


if __name__ == "__main__":
    unittest.main()
