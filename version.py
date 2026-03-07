"""
Deploy identity helper.

Returns a short string identifying the currently-running revision so that
production logs (e.g. on Railway) make it unambiguous which commit is live.

Resolution order:
1. ``DEPLOY_VERSION`` environment variable – set this in your Railway /
   Docker / CI config to the git SHA or release tag at deploy time.
2. ``git rev-parse --short HEAD`` – works in local dev and in environments
   where the ``.git`` directory is present at runtime.
3. ``"unknown"`` – safe fallback; never raises.
"""
from __future__ import annotations

import os
import subprocess


def get_version() -> str:
    """Return a short deploy identifier, never raises."""
    # 1. Explicit env var (preferred in production / CI)
    env_val = os.environ.get("DEPLOY_VERSION", "").strip()
    if env_val:
        return env_val

    # 2. Git SHA from the repository (works in dev / image-with-.git)
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=3,
        )
        if result.returncode == 0:
            sha = result.stdout.strip()
            if sha:
                return sha
    except Exception:
        pass

    return "unknown"


__all__ = ["get_version"]
