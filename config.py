"""
Safe configuration loader.

Notes:
- This module DOES NOT call Config.load() at import time to avoid crashes
  during build when runtime environment variables are not available.
- Use `Config.load()` at runtime (e.g. inside main()) to obtain the config.
"""
import os
from dataclasses import dataclass
from typing import Optional, List


def _env(key: str, required: bool = False, default: Optional[str] = None) -> Optional[str]:
    """Get environment variable, strip whitespace, optionally require it."""
    val = os.environ.get(key, default)
    if isinstance(val, str):
        val = val.strip()
    if required and not val:
        raise RuntimeError(f"Missing required env var: {key}")
    return val


@dataclass
class Config:
    bot_token: str
    database_url: Optional[str] = None
    provider_token: Optional[str] = None
    channel_id: Optional[str] = None
    autopost_interval_hours: int = 6
    api_model: Optional[str] = None
    admin_user_ids: Optional[str] = None  # comma-separated string of ids
    images_enabled: bool = True
    payments_enabled: bool = False

    # Optional API keys that might exist in the repo/config
    pexels_api_key: Optional[str] = None
    pixabay_api_key: Optional[str] = None
    pplx_api_key: Optional[str] = None

    @classmethod
    def load(cls) -> "Config":
        # support both correct and historical misspelled env var names
        autopost_env = _env("AUTOPOST_INTERVAL_HOURS", required=False)
        autopost_env_alt = _env("AUTPOST_INTERVAL_HOURS", required=False)
        autopost_value = autopost_env or autopost_env_alt or _env("AUTPOST_INTERVAL_HOURS", required=False, default="6")

        try:
            autopost_hours = int(autopost_value) if autopost_value is not None else 6
        except (TypeError, ValueError):
            autopost_hours = 6

        images_enabled = (_env("IMAGES_ENABLED", required=False, default="True").lower() == "true")
        payments_enabled = (_env("PAYMENTS_ENABLED", required=False, default="False").lower() == "true")

        return cls(
            bot_token=_env("BOT_TOKEN", required=True),
            database_url=_env("DATABASE_URL", required=False),
            provider_token=_env("PROVIDER_TOKEN", required=False),
            channel_id=_env("CHANNEL_ID", required=False),
            autopost_interval_hours=autopost_hours,
            api_model=_env("API_MODEL", required=False, default="sonar-small"),
            admin_user_ids=_env("ADMIN_USER_IDS", required=False),
            images_enabled=images_enabled,
            payments_enabled=payments_enabled,
            pexels_api_key=_env("PEXELS_API_KEY", required=False),
            pixabay_api_key=_env("PIXABAY_API_KEY", required=False),
            pplx_api_key=_env("PPLX_API_KEY", required=False),
        )

    # convenience helpers
    def has_bot_token(self) -> bool:
        return bool(self.bot_token and self.bot_token.strip())

    def has_api_key(self) -> bool:
        return bool(self.pplx_api_key and self.pplx_api_key.strip())

    def parse_admin_user_ids(self) -> List[int]:
        """Return admin user ids as list of ints. Ignore invalid entries."""
        if not self.admin_user_ids:
            return []
        parts = [p.strip() for p in self.admin_user_ids.split(",") if p.strip()]
        ids = []
        for p in parts:
            try:
                ids.append(int(p))
            except ValueError:
                # ignore non-integer entries
                continue
        return ids

    def get_safe_config_info(self) -> dict:
        """Return a safe-to-log summary of config (no secrets)."""
        admin_ids = self.parse_admin_user_ids()
        return {
            "channel_id": self.channel_id,
            "autopost_interval_hours": self.autopost_interval_hours,
            "api_model": self.api_model,
            "admin_user_count": len(admin_ids),
            "images_enabled": bool(self.pexels_api_key or self.pixabay_api_key or self.images_enabled),
            "payments_enabled": bool(self.provider_token or self.payments_enabled),
        }


__all__ = ["Config"]
