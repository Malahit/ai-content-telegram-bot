"""
Subscription middleware for checking user access to premium features.

This middleware can be used to restrict certain commands to premium users only.
It also injects the user's effective daily post limit (accounting for referral bonuses)
into the handler data.
"""

from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import Message

from services.user_service import is_premium, get_user
from logger_config import logger

# Base free daily post limit
FREE_DAILY_LIMIT = 3


class SubscriptionMiddleware(BaseMiddleware):
    """
    Middleware to check if user has premium access for certain features.

    Also injects ``effective_daily_limit`` into handler data, which accounts
    for referral bonus posts on top of FREE_DAILY_LIMIT.
    """

    def __init__(self, premium_commands: list = None):
        """
        Initialize the middleware.

        Args:
            premium_commands: List of command names that require premium access.
                            If None, middleware only logs but doesn't restrict.
        """
        super().__init__()
        self.premium_commands = premium_commands or []

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        """
        Process the message and check for premium access if needed.

        Also computes effective_daily_limit = FREE_DAILY_LIMIT + user.referral_bonus_posts
        and passes it in data for downstream handlers.

        Args:
            handler: Next handler in the chain
            event: The message event
            data: Additional data

        Returns:
            Result from the next handler or None if access is denied
        """
        # Skip non-message events
        if not isinstance(event, Message):
            return await handler(event, data)

        # Compute effective daily limit with referral bonus
        if event.from_user:
            user = await get_user(event.from_user.id)
            if user:
                bonus = getattr(user, "referral_bonus_posts", 0) or 0
                data["effective_daily_limit"] = FREE_DAILY_LIMIT + bonus
            else:
                data["effective_daily_limit"] = FREE_DAILY_LIMIT

        # Check if this is a command that requires premium
        if event.text and event.text.startswith('/'):
            command = event.text.split()[0][1:]  # Remove the '/' prefix

            if command in self.premium_commands:
                user_id = event.from_user.id
                user_is_premium = await is_premium(user_id)

                if not user_is_premium:
                    logger.info(f"User {user_id} attempted to use premium command: /{command}")
                    await event.answer(
                        f"🔒 <b>Premium Feature</b>\n\n"
                        f"The /{command} command is only available for premium subscribers.\n\n"
                        f"Upgrade to premium to unlock this and other exclusive features!\n"
                        f"Use /subscribe to get started.",
                        parse_mode="HTML"
                    )
                    return None  # Don't pass to next handler

        # Continue to next handler
        return await handler(event, data)
