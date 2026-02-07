import os
from dataclasses import dataclass
from typing import List

def _env(key: str, default=None, required=False, cast=str):
    val = os.getenv(key, default)
    if required and (val is None or val == ""):
        raise RuntimeError(f"Missing required env var: {key}")
    try:
        return cast(val) if val is not None else val
    except Exception:
        return val

def _list_env(key: str) -> List[int]:
    raw = os.getenv(key, "")
    if not raw:
        return []
    return [int(x) for x in raw.replace(" ", "").split(",") if x]

@dataclass
class Config:
    bot_token: str
    pplx_api_key: str
    channel_id: str | None
    admin_user_ids: List[int]
    api_timeout: int
    max_tokens: int
    temperature: float
    api_model: str
    provider_token: str | None
    autopost_interval_hours: int
    pexels_api_key: str | None
    pixabay_api_key: str | None

    @classmethod
    def load(cls):
        return cls(
            bot_token=_env("BOT_TOKEN", required=True),
            pplx_api_key=_env("PPLX_API_KEY", required=True),
            channel_id=_env("CHANNEL_ID"),
            admin_user_ids=_list_env("ADMIN_USER_IDS"),
            api_timeout=_env("API_TIMEOUT", 30, cast=int),
            max_tokens=_env("MAX_TOKENS", 4000, cast=int),
            temperature=_env("TEMPERATURE", 0.7, cast=float),
            api_model=_env("API_MODEL", "sonar-small"),
            provider_token=_env("PROVIDER_TOKEN"),
            autopost_interval_hours=_env("AUTOPOST_INTERVAL_HOURS", 6, cast=int),
            pexels_api_key=_env("PEXELS_API_KEY"),
            pixabay_api_key=_env("PIXABAY_API_KEY"),
        )

    def has_bot_token(self): return bool(self.bot_token)
    def has_api_key(self): return bool(self.pplx_api_key)
    def get_safe_config_info(self):
        return {
            "channel_id": self.channel_id,
            "autopost_interval_hours": self.autopost_interval_hours,
            "api_model": self.api_model,
            "admin_user_ids": len(self.admin_user_ids),
            "images_enabled": bool(self.pexels_api_key or self.pixabay_api_key),
            "payments_enabled": bool(self.provider_token),
        }

config = Config.load()
__all__ = ["config", "Config"]