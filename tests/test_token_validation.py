"""
Regression tests for BOT_TOKEN format validation.

The ``_validate_bot_token`` helper in bot.py provides fail-fast startup: the
process exits immediately with a clear error message if the token is missing
or malformed, rather than failing later with a cryptic Telegram API error.

These tests exercise the regex pattern and edge cases without importing bot.py
(which would require live env vars and trigger Bot instantiation).

Background: BotFather tokens have the format ``<numeric_id>:<alphanumeric_string>``.
Common mistakes that should be caught:
- Forgetting to set the variable entirely (empty / None)
- Pasting with surrounding quotes
- Including the ``Bot `` prefix from some documentation
- Extra whitespace from copy-paste
"""

import re
import sys
import os
import ast
import unittest

# Make sure the project root is on the path
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

# The regex pattern used by _validate_bot_token() in bot.py.
# Kept in sync by the test_pattern_matches_bot_py_source test below.
_EXPECTED_PATTERN = re.compile(r"^\d+:[A-Za-z0-9_-]+$")


class TestBotTokenValidationPattern(unittest.TestCase):
    """
    PR #2 regression: verify the token validation pattern accepts real tokens
    and rejects common invalid inputs.
    """

    # ------------------------------------------------------------------
    # Valid token formats
    # ------------------------------------------------------------------

    def test_typical_token_accepted(self):
        """Standard BotFather token format must be accepted."""
        self.assertRegex("123456789:ABCdefGHIjklMNOpqrSTUvwxyz", _EXPECTED_PATTERN)

    def test_token_with_underscores_accepted(self):
        """Tokens containing underscores must be accepted."""
        self.assertRegex("987654321:ABC_def_GHI", _EXPECTED_PATTERN)

    def test_token_with_dashes_accepted(self):
        """Tokens containing dashes must be accepted."""
        self.assertRegex("111222333:ABC-def-GHI", _EXPECTED_PATTERN)

    def test_short_secret_accepted(self):
        """Tokens with a short secret part must still be accepted."""
        self.assertRegex("1:A", _EXPECTED_PATTERN)

    def test_long_real_looking_token_accepted(self):
        """Realistic-length token (BotFather output) must be accepted."""
        self.assertRegex("7123456789:AAH1a2B3c4D5e6F7g8H9i0J1k2L3m4N5o6P", _EXPECTED_PATTERN)

    # ------------------------------------------------------------------
    # Invalid token formats (common operator mistakes)
    # ------------------------------------------------------------------

    def test_empty_string_rejected(self):
        """Empty string must NOT match (token not configured)."""
        self.assertNotRegex("", _EXPECTED_PATTERN)

    def test_whitespace_only_rejected(self):
        """Whitespace-only string must NOT match."""
        self.assertNotRegex("   ", _EXPECTED_PATTERN)

    def test_missing_colon_rejected(self):
        """Token without the ``:`` separator must NOT match."""
        self.assertNotRegex("123456789ABCdef", _EXPECTED_PATTERN)

    def test_bot_prefix_rejected(self):
        """``Bot <token>`` (prefix from some docs) must NOT match."""
        self.assertNotRegex("Bot 123456789:ABCdef", _EXPECTED_PATTERN)

    def test_token_with_spaces_rejected(self):
        """Token containing embedded spaces must NOT match."""
        self.assertNotRegex("123456789:ABC def", _EXPECTED_PATTERN)

    def test_non_numeric_id_rejected(self):
        """Token whose ID part is non-numeric must NOT match."""
        self.assertNotRegex("abc:ABCdef", _EXPECTED_PATTERN)

    def test_quoted_token_rejected(self):
        """Token wrapped in double-quotes (copy-paste mistake) must NOT match."""
        self.assertNotRegex('"123456789:ABCdef"', _EXPECTED_PATTERN)

    def test_single_quoted_token_rejected(self):
        """Token wrapped in single-quotes must NOT match."""
        self.assertNotRegex("'123456789:ABCdef'", _EXPECTED_PATTERN)

    def test_leading_whitespace_rejected(self):
        """Token with a leading space must NOT match (strip() not applied by regex)."""
        self.assertNotRegex(" 123456789:ABCdef", _EXPECTED_PATTERN)

    def test_trailing_whitespace_rejected(self):
        """Token with a trailing space must NOT match."""
        self.assertNotRegex("123456789:ABCdef ", _EXPECTED_PATTERN)


class TestBotPyUsesExpectedPattern(unittest.TestCase):
    """
    Verify that bot.py still contains the same regex so the tests above stay
    in sync with the actual validation logic.
    """

    def setUp(self):
        bot_py = os.path.join(_ROOT, "bot.py")
        with open(bot_py) as fh:
            self._source = fh.read()
        self._tree = ast.parse(self._source, filename="bot.py")

    def _get_validate_func(self):
        """Return the AST node for _validate_bot_token, or None."""
        for node in ast.iter_child_nodes(self._tree):
            if (
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name == "_validate_bot_token"
            ):
                return node
        return None

    def test_pattern_present_in_bot_py_source(self):
        """The expected validation regex must appear in bot.py."""
        self.assertIn(
            r"^\d+:[A-Za-z0-9_-]+$",
            self._source,
            "bot.py must contain the BOT_TOKEN validation regex r'^\\d+:[A-Za-z0-9_-]+$'",
        )

    def test_validate_bot_token_function_defined(self):
        """bot.py must define _validate_bot_token() (AST check)."""
        self.assertIsNotNone(
            self._get_validate_func(),
            "bot.py must define _validate_bot_token() for fail-fast startup",
        )

    def test_validate_bot_token_raises_on_empty_token(self):
        """_validate_bot_token must terminate the process for an empty/missing token.

        Verified via AST: the function body must contain at least one ``raise``
        statement (SystemExit or similar).  This is more resilient than
        matching exact error-message text, which can be freely rephrased.
        """
        func_node = self._get_validate_func()
        self.assertIsNotNone(func_node, "bot.py must define _validate_bot_token()")
        raises = [n for n in ast.walk(func_node) if isinstance(n, ast.Raise)]
        self.assertGreaterEqual(
            len(raises),
            1,
            "_validate_bot_token must raise (e.g. SystemExit) when the token is empty/missing",
        )

    def test_validate_bot_token_raises_on_invalid_format(self):
        """_validate_bot_token must terminate for a token with an invalid format.

        Verified via AST: the function body must contain at least two distinct
        ``raise`` statements — one for the empty-token case and one for the
        bad-format case.  Checking the count avoids coupling the test to exact
        error-message wording.
        """
        func_node = self._get_validate_func()
        self.assertIsNotNone(func_node, "bot.py must define _validate_bot_token()")
        raises = [n for n in ast.walk(func_node) if isinstance(n, ast.Raise)]
        self.assertGreaterEqual(
            len(raises),
            2,
            "_validate_bot_token must have separate raise paths for empty and invalid-format tokens",
        )


if __name__ == "__main__":
    unittest.main()
