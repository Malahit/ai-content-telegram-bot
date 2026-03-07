"""
Unit tests for version.py deploy identity helper.
"""
import os
import subprocess
import unittest
from unittest.mock import patch, MagicMock


class TestGetVersion(unittest.TestCase):
    """Tests for version.get_version()."""

    def _import_fresh(self):
        """Re-import version module so module-level cache doesn't interfere."""
        import importlib
        import version
        importlib.reload(version)
        return version.get_version

    def test_returns_deploy_version_env_var_when_set(self):
        """DEPLOY_VERSION env var takes highest priority."""
        with patch.dict(os.environ, {"DEPLOY_VERSION": "abc1234"}):
            from version import get_version
            self.assertEqual(get_version(), "abc1234")

    def test_strips_whitespace_from_deploy_version(self):
        """DEPLOY_VERSION env var value is stripped of whitespace."""
        with patch.dict(os.environ, {"DEPLOY_VERSION": "  abc1234  "}):
            from version import get_version
            self.assertEqual(get_version(), "abc1234")

    def test_falls_back_to_git_sha_when_env_var_absent(self):
        """Falls back to git rev-parse when DEPLOY_VERSION is not set."""
        env_without_version = {k: v for k, v in os.environ.items() if k != "DEPLOY_VERSION"}
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "deadbeef\n"
        with patch.dict(os.environ, env_without_version, clear=True):
            with patch("subprocess.run", return_value=mock_result) as mock_run:
                from version import get_version
                result = get_version()
                self.assertEqual(result, "deadbeef")
                mock_run.assert_called_once_with(
                    ["git", "rev-parse", "--short", "HEAD"],
                    capture_output=True,
                    text=True,
                    timeout=3,
                )

    def test_returns_unknown_when_git_fails(self):
        """Returns 'unknown' when git command raises an exception."""
        env_without_version = {k: v for k, v in os.environ.items() if k != "DEPLOY_VERSION"}
        with patch.dict(os.environ, env_without_version, clear=True):
            with patch("subprocess.run", side_effect=FileNotFoundError("git not found")):
                from version import get_version
                self.assertEqual(get_version(), "unknown")

    def test_returns_unknown_when_git_returns_empty(self):
        """Returns 'unknown' when git returns empty output."""
        env_without_version = {k: v for k, v in os.environ.items() if k != "DEPLOY_VERSION"}
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "   "
        with patch.dict(os.environ, env_without_version, clear=True):
            with patch("subprocess.run", return_value=mock_result):
                from version import get_version
                self.assertEqual(get_version(), "unknown")

    def test_returns_unknown_when_git_nonzero_exit(self):
        """Returns 'unknown' when git exits with non-zero status (not a git repo, etc.)."""
        env_without_version = {k: v for k, v in os.environ.items() if k != "DEPLOY_VERSION"}
        mock_result = MagicMock()
        mock_result.returncode = 128
        mock_result.stdout = "fatal: not a git repository\n"
        with patch.dict(os.environ, env_without_version, clear=True):
            with patch("subprocess.run", return_value=mock_result):
                from version import get_version
                self.assertEqual(get_version(), "unknown")

    def test_deploy_version_empty_string_falls_through(self):
        """Empty DEPLOY_VERSION env var is treated as unset."""
        env_without_version = {k: v for k, v in os.environ.items() if k != "DEPLOY_VERSION"}
        env_without_version["DEPLOY_VERSION"] = ""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "cafebabe\n"
        with patch.dict(os.environ, env_without_version, clear=True):
            with patch("subprocess.run", return_value=mock_result):
                from version import get_version
                result = get_version()
                self.assertEqual(result, "cafebabe")

    def test_never_raises(self):
        """get_version() must never raise even when everything fails."""
        env_without_version = {k: v for k, v in os.environ.items() if k != "DEPLOY_VERSION"}
        with patch.dict(os.environ, env_without_version, clear=True):
            with patch("subprocess.run", side_effect=Exception("unexpected")):
                from version import get_version
                try:
                    result = get_version()
                except Exception as exc:
                    self.fail(f"get_version() raised unexpectedly: {exc}")
                self.assertEqual(result, "unknown")


if __name__ == "__main__":
    unittest.main()
