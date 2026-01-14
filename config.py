"""
Configuration module for AI Content Telegram Bot.

This module handles all environment variable loading and configuration validation.
Sensitive information is kept secure and not exposed in logs.
"""

import os
from typing import Optional
from dotenv import load_dotenv


class Config:
    """
    Application configuration class.
    
    Loads and validates all required environment variables.
    Provides secure access to sensitive configuration without exposing values.
    """
    
    def __init__(self):
        """Initialize configuration by loading environment variables."""
        load_dotenv()
        self._load_config()
        self._validate_config()
    
    def _load_config(self) -> None:
        """Load all configuration from environment variables."""
        # Bot Configuration
        self.bot_token: Optional[str] = os.getenv("BOT_TOKEN") or None
        # Try PPLX_API_KEY first, then fall back to PERPLEXITY_API_KEY
        self.pplx_api_key: Optional[str] = os.getenv("PPLX_API_KEY") or os.getenv("PERPLEXITY_API_KEY") or None
        self.channel_id: str = os.getenv("CHANNEL_ID", "@content_ai_helper_bot")
        
        # API Configuration
        self.api_timeout: int = int(os.getenv("API_TIMEOUT", "45"))
        self.max_tokens: int = int(os.getenv("MAX_TOKENS", "800"))
        self.temperature: float = float(os.getenv("TEMPERATURE", "0.8"))
        self.api_model: str = os.getenv("API_MODEL", "sonar")
        
        # Scheduler Configuration
        self.autopost_interval_hours: int = int(os.getenv("AUTOPOST_INTERVAL_HOURS", "6"))
        
        # RAG Configuration
        self.rag_search_k: int = int(os.getenv("RAG_SEARCH_K", "2"))
        self.rag_context_max_chars: int = int(os.getenv("RAG_CONTEXT_MAX_CHARS", "400"))
        
        # Image Configuration
        self.pexels_api_key: Optional[str] = os.getenv("PEXELS_API_KEY") or None
        
        # Admin Configuration
        admin_ids_str = os.getenv("ADMIN_USER_IDS", "")
        self.admin_user_ids: list = [int(uid.strip()) for uid in admin_ids_str.split(",") if uid.strip().isdigit()] if admin_ids_str else []
    
    def _validate_config(self) -> None:
        """Validate required configuration values."""
        if not self.bot_token:
            raise RuntimeError("❌ BOT_TOKEN не найден в .env!")
        if not self.pplx_api_key:
            raise RuntimeError("❌ PPLX_API_KEY не найден в .env!")
    
    def has_bot_token(self) -> bool:
        """Check if bot token is configured."""
        return bool(self.bot_token)
    
    def has_api_key(self) -> bool:
        """Check if Perplexity API key is configured."""
        return bool(self.pplx_api_key)
    
    def get_safe_config_info(self) -> dict:
        """
        Get safe configuration info for logging (without sensitive data).
        
        Returns:
            dict: Configuration information safe for logging
        """
        return {
            "bot_token_configured": self.has_bot_token(),
            "api_key_configured": self.has_api_key(),
            "pexels_api_key_configured": bool(self.pexels_api_key),
            "channel_id": self.channel_id,
            "api_model": self.api_model,
            "autopost_interval_hours": self.autopost_interval_hours,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "admin_users_count": len(self.admin_user_ids)
        }


def get_config() -> Config:
    """
    Get or create the global configuration instance.
    
    Returns:
        Config: The global configuration instance
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance


# Global configuration instance (lazy-loaded)
_config_instance: Optional[Config] = None
config = get_config()
