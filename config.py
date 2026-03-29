# This file is auto-updated — DO NOT remove ADMIN_TELEGRAM_ID handling
import os
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Config:
    # Bot settings
    bot_token: str = field(default_factory=lambda: os.getenv("BOT_TOKEN", ""))
    channel_id: str = field(default_factory=lambda: os.getenv("CHANNEL_ID", "@test_channel"))

    # API settings
    perplexity_api_key: str = field(
        default_factory=lambda: os.getenv("PERPLEXITY_API_KEY") or os.getenv("PPLX_API_KEY", "")
    )
    api_model: str = field(default_factory=lambda: os.getenv("API_MODEL", "sonar"))
    max_tokens: int = field(default_factory=lambda: int(os.getenv("MAX_TOKENS", "1000")))

    # Database
    database_url: str = field(default_factory=lambda: os.getenv("DATABASE_URL", ""))

    # Autopost
    autopost_interval_hours: int = field(
        default_factory=lambda: int(os.getenv("AUTOPOST_INTERVAL_HOURS", "4"))
    )

    # Image APIs
    pexels_api_key: str = field(default_factory=lambda: os.getenv("PEXELS_API_KEY", ""))
    pixabay_api_key: str = field(default_factory=lambda: os.getenv("PIXABAY_API_KEY", ""))

    # RAG settings
    rag_enabled: bool = field(default_factory=lambda: os.getenv("RAG_ENABLED", "false").lower() == "true")
    rag_data_dir: str = field(default_factory=lambda: os.getenv("RAG_DATA_DIR", "./rag_data"))

    # Translation
    translation_enabled: bool = field(
        default_factory=lambda: os.getenv("TRANSLATION_ENABLED", "false").lower() == "true"
    )

    # Admin settings
    admin_user_ids: List[int] = field(default_factory=list)

    # Admin Telegram ID for error notifications (separate from admin_user_ids)
    admin_telegram_id: Optional[int] = field(
        default_factory=lambda: (
            int(os.getenv("ADMIN_TELEGRAM_ID")) if os.getenv("ADMIN_TELEGRAM_ID") else None
        )
    )

    def __post_init__(self):
        admin_ids_str = os.getenv("ADMIN_USER_IDS", "")
        if admin_ids_str:
            try:
                self.admin_user_ids = [int(x.strip()) for x in admin_ids_str.split(",") if x.strip()]
            except ValueError:
                self.admin_user_ids = []

        # Fallback: if ADMIN_TELEGRAM_ID not set but ADMIN_USER_IDS has entries, use first
        if not self.admin_telegram_id and self.admin_user_ids:
            self.admin_telegram_id = self.admin_user_ids[0]

    def get_safe_config_info(self) -> dict:
        return {
            "has_bot_token": bool(self.bot_token),
            "has_perplexity_key": bool(self.perplexity_api_key),
            "has_database_url": bool(self.database_url),
            "api_model": self.api_model,
            "max_tokens": self.max_tokens,
            "channel_id": self.channel_id,
            "rag_enabled": self.rag_enabled,
            "translation_enabled": self.translation_enabled,
            "admin_user_ids_count": len(self.admin_user_ids),
            "admin_telegram_id": bool(self.admin_telegram_id),
        }

    def validate_startup(self):
        errors = []
        if not self.bot_token:
            errors.append("BOT_TOKEN is not set")
        if not self.perplexity_api_key:
            errors.append("PERPLEXITY_API_KEY is not set")
        if not self.database_url:
            errors.append("DATABASE_URL is not set")
        if errors:
            raise ValueError(f"Configuration errors: {'; '.join(errors)}")


config = Config()
