"""
Subscription middleware — enforces daily post limits for free users.

Applied ONLY to content-generation handlers (📝 Пост, /generate).
System commands (/start, /help, /status, /subscribe, /admin, etc.) pass freely.

Also injects the user's effective daily post limit (accounting for referral bonuses)
into the handler data.
"""

import os
from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import Message

from services.user_service import get_user
from services.usage_service import get_today_post_count
from logger_config import logger

# Base free daily post limit
FREE_DAILY_LIMIT = 3


# Texts/buttons that trigger content generation and should be rate-limited
_CONTENT_GENERATION_TRIGGERS = frozenset({
    "📝 Пост",
})

_CONTENT_GENERATION_COMMANDS = frozenset({
    "generate",
})

FREE_DAILY_LIMIT = int(os.getenv("FREE_DAILY_LIMIT", "3"))
PRO_DAILY_LIMIT = int(os.getenv("PRO_DAILY_LIMIT", "30"))


class SubscriptionMiddleware(BaseMiddleware):
    """Checks daily limit for free users on content-generation handlers.

    Also injects ``effective_daily_limit`` into handler data, which accounts
    for referral bonus posts on top of FREE_DAILY_LIMIT.
    """

    def __init__(self, premium_commands: list | None = None):
        """Accept premium_commands for backward compat (ignored, kept as attr)."""
        super().__init__()
        self.premium_commands = premium_commands or []

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any],
    ) -> Any:
        # Only intercept Message events
        if not isinstance(event, Message):
            return await handler(event, data)

        text = (event.text or "").strip()

        # Determine if this message triggers content generation
        is_generation = False
        if text in _CONTENT_GENERATION_TRIGGERS:
            is_generation = True
        elif text.startswith("/"):
            cmd = text.split()[0][1:].split("@")[0]  # strip /cmd@botname
            if cmd in _CONTENT_GENERATION_COMMANDS:
                is_generation = True

        if not is_generation:
            # System command / menu button — pass through without premium check
            return await handler(event, data)

        # Content generation path — check daily limit
        user = await get_user(event.from_user.id)
        is_premium = False
        if user:
            is_premium = bool(user.is_premium and (
                user.subscription_end is None
                or user.subscription_end > __import__("datetime").datetime.utcnow()
            ))

        data["is_premium"] = is_premium

        if not is_premium:
            # Compute effective daily limit with referral bonus
            bonus = getattr(user, "referral_bonus_posts", 0) or 0
            effective_limit = FREE_DAILY_LIMIT + bonus
            data["effective_daily_limit"] = effective_limit

            today_count = await get_today_post_count(event.from_user.id)
            if today_count >= effective_limit:
                await event.answer(
                    f"⚠️ Дневной лимит исчерпан ({today_count}/{effective_limit})\n\n"
                    "💎 Безлимитный доступ: /subscribe\n"
                    "• 30 постов в день\n"
                    "• Продвинутая модель AI\n"
                    "• Без водяного знака\n"
                    "• Выбор стиля и длины\n\n"
                    "🔗 Или пригласи друга: /referral"
                )
                logger.info(
                    f"User {event.from_user.id} hit free daily limit "
                    f"({today_count}/{effective_limit})"
                )
                return None  # Block handler

        return await handler(event, data)
