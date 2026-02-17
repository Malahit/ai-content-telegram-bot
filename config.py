"""
Configuration loader (backward-compatible).

- Keeps `Config()` behavior expected by the codebase/tests.
- Exposes module-level `config` for `from config import config`.
- Uses lazy loading for `config` to avoid import-time crashes when env is absent.
"""
from __future__ import annotations

import os
from typing import Optional, List, Any


def _env(key: str, required: bool = False, default: Optional[str] = None) -> Optional[str]:
    val = os.environ.get(key, default)
    if isinstance(val, str):
        val = val.strip()
    if required and not val:
        raise RuntimeError(f"Missing required env var: {key}")
    return val


def _parse_int_list(csv: Optional[str]) -> List[int]:
    if not csv:
        return []
    out: List[int] = []
    for part in csv.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            out.append(int(part))
        except ValueError:
            continue
    return out


class Config:
    def __init__(self) -> None:
        self.bot_token: str = _env("BOT_TOKEN", required=True)  # type: ignore[assignment]
        self.pplx_api_key: str = _env("PPLX_API_KEY", required=True)  # type: ignore[assignment]

        self.channel_id: Optional[str] = _env("CHANNEL_ID", required=False)
        self.provider_token: Optional[str] = _env("PROVIDER_TOKEN", required=False)
        self.database_url: Optional[str] = _env("DATABASE_URL", required=False)

        # Perplexity/API params expected by api_client.py
        self.api_model: str = _env("API_MODEL", required=False, default="sonar-small") or "sonar-small"
        self.api_timeout: int = int(_env("API_TIMEOUT", required=False, default="30") or "30")
        self.max_tokens: int = int(_env("MAX_TOKENS", required=False, default="800") or "800")
        self.temperature: float = float(_env("TEMPERATURE", required=False, default="0.7") or "0.7")

        # Autopost interval (support historical misspelling)
        autopost = _env("AUTOPOST_INTERVAL_HOURS", required=False) or _env("AUTPOST_INTERVAL_HOURS", required=False) or "6"
        try:
            self.autopost_interval_hours: int = int(autopost)
        except ValueError:
            self.autopost_interval_hours = 6

        # Admins
        self.admin_user_ids: List[int] = _parse_int_list(_env("ADMIN_USER_IDS", required=False))

        # Images
        self.pexels_api_key: Optional[str] = _env("PEXELS_API_KEY", required=False)
        self.pixabay_api_key: Optional[str] = _env("PIXABAY_API_KEY", required=False)

    @classmethod
    def load(cls) -> "Config":
        return cls()

    def has_bot_token(self) -> bool:
        return bool(self.bot_token and self.bot_token.strip())

    def has_api_key(self) -> bool:
        return bool(self.pplx_api_key and self.pplx_api_key.strip())

    def get_safe_config_info(self) -> dict:
        return {
            "bot_token_configured": bool(self.bot_token),
            "api_key_configured": bool(self.pplx_api_key),
            "channel_id": self.channel_id,
            "api_model": self.api_model,
            "admin_user_count": len(self.admin_user_ids),
            "images_enabled": bool(self.pexels_api_key or self.pixabay_api_key),
            "payments_enabled": bool(self.provider_token),
        }


class _LazyConfig:
    _instance: Optional[Config] = None

    def _get(self) -> Config:
        if self._instance is None:
            self._instance = Config()
        return self._instance

    def __getattr__(self, name: str) -> Any:
        return getattr(self._get(), name)


config = _LazyConfig()

__all__ = ["Config", "config"]
