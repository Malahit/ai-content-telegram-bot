"""
Unit tests for SubscriptionMiddleware — daily limit enforcement.

The middleware enforces FREE_DAILY_LIMIT on content-generation handlers
(📝 Пост, /generate) while letting system commands pass freely.
"""

import asyncio
import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aiogram.types import Message
from middlewares.subscription_middleware import SubscriptionMiddleware


def _make_message(text: str, user_id: int = 123) -> MagicMock:
    msg = MagicMock()
    msg.__class__ = Message
    msg.text = text
    msg.from_user = MagicMock()
    msg.from_user.id = user_id
    msg.answer = AsyncMock()
    return msg


class TestMiddlewarePassThrough(unittest.TestCase):
    """System commands and non-generation messages should always pass."""

    def setUp(self):
        self.middleware = SubscriptionMiddleware()

    def _run(self, coro):
        return asyncio.run(coro)

    def test_start_command_passes(self):
        handler = AsyncMock(return_value="ok")
        msg = _make_message("/start")
        result = self._run(self.middleware(handler, msg, {}))
        handler.assert_awaited_once_with(msg, {})
        self.assertEqual(result, "ok")

    def test_help_command_passes(self):
        handler = AsyncMock(return_value="ok")
        msg = _make_message("/help")
        result = self._run(self.middleware(handler, msg, {}))
        handler.assert_awaited_once()

    def test_subscribe_command_passes(self):
        handler = AsyncMock(return_value="ok")
        msg = _make_message("/subscribe")
        result = self._run(self.middleware(handler, msg, {}))
        handler.assert_awaited_once()

    def test_status_command_passes(self):
        handler = AsyncMock(return_value="ok")
        msg = _make_message("/status")
        result = self._run(self.middleware(handler, msg, {}))
        handler.assert_awaited_once()

    def test_admin_command_passes(self):
        handler = AsyncMock(return_value="ok")
        msg = _make_message("/admin")
        result = self._run(self.middleware(handler, msg, {}))
        handler.assert_awaited_once()

    def test_plain_text_passes(self):
        handler = AsyncMock(return_value="ok")
        msg = _make_message("hello world")
        result = self._run(self.middleware(handler, msg, {}))
        handler.assert_awaited_once()

    def test_subscriptions_button_passes(self):
        handler = AsyncMock(return_value="ok")
        msg = _make_message("📬 Подписки")
        result = self._run(self.middleware(handler, msg, {}))
        handler.assert_awaited_once()

    def test_non_message_event_passes(self):
        handler = AsyncMock(return_value="cb_result")
        event = MagicMock(spec=[])
        result = self._run(self.middleware(handler, event, {}))
        handler.assert_awaited_once()


class TestMiddlewareLimitEnforcement(unittest.TestCase):
    """Content generation triggers should be rate-limited for free users."""

    def setUp(self):
        self.middleware = SubscriptionMiddleware()

    def _run(self, coro):
        return asyncio.run(coro)

    @patch("middlewares.subscription_middleware.get_today_post_count", new_callable=AsyncMock)
    @patch("middlewares.subscription_middleware.get_user", new_callable=AsyncMock)
    def test_free_user_under_limit_allowed(self, mock_get_user, mock_count):
        mock_user = MagicMock()
        mock_user.is_premium = False
        mock_get_user.return_value = mock_user
        mock_count.return_value = 1

        handler = AsyncMock(return_value="ok")
        msg = _make_message("📝 Пост", user_id=42)
        data = {}

        result = self._run(self.middleware(handler, msg, data))

        handler.assert_awaited_once()
        self.assertEqual(result, "ok")
        self.assertFalse(data.get("is_premium"))

    @patch("middlewares.subscription_middleware.get_today_post_count", new_callable=AsyncMock)
    @patch("middlewares.subscription_middleware.get_user", new_callable=AsyncMock)
    def test_free_user_at_limit_blocked(self, mock_get_user, mock_count):
        mock_user = MagicMock()
        mock_user.is_premium = False
        mock_get_user.return_value = mock_user
        mock_count.return_value = 3  # At FREE_DAILY_LIMIT

        handler = AsyncMock()
        msg = _make_message("📝 Пост", user_id=42)

        result = self._run(self.middleware(handler, msg, {}))

        handler.assert_not_awaited()
        msg.answer.assert_awaited_once()
        answer_text = msg.answer.call_args[0][0]
        self.assertIn("Дневной лимит", answer_text)
        self.assertIsNone(result)

    @patch("middlewares.subscription_middleware.get_today_post_count", new_callable=AsyncMock)
    @patch("middlewares.subscription_middleware.get_user", new_callable=AsyncMock)
    def test_free_user_over_limit_blocked(self, mock_get_user, mock_count):
        mock_user = MagicMock()
        mock_user.is_premium = False
        mock_get_user.return_value = mock_user
        mock_count.return_value = 5

        handler = AsyncMock()
        msg = _make_message("/generate", user_id=42)

        result = self._run(self.middleware(handler, msg, {}))

        handler.assert_not_awaited()
        msg.answer.assert_awaited_once()
        self.assertIsNone(result)

    @patch("middlewares.subscription_middleware.get_user", new_callable=AsyncMock)
    def test_premium_user_always_allowed(self, mock_get_user):
        from datetime import datetime, timedelta
        mock_user = MagicMock()
        mock_user.is_premium = True
        mock_user.subscription_end = datetime.utcnow() + timedelta(days=10)
        mock_get_user.return_value = mock_user

        handler = AsyncMock(return_value="ok")
        msg = _make_message("📝 Пост", user_id=99)
        data = {}

        result = self._run(self.middleware(handler, msg, data))

        handler.assert_awaited_once()
        self.assertTrue(data.get("is_premium"))

    @patch("middlewares.subscription_middleware.get_today_post_count", new_callable=AsyncMock)
    @patch("middlewares.subscription_middleware.get_user", new_callable=AsyncMock)
    def test_generate_command_with_bot_username(self, mock_get_user, mock_count):
        """Test /generate@botname is also rate-limited."""
        mock_user = MagicMock()
        mock_user.is_premium = False
        mock_get_user.return_value = mock_user
        mock_count.return_value = 3

        handler = AsyncMock()
        msg = _make_message("/generate@ai_content_helper_bot", user_id=42)

        result = self._run(self.middleware(handler, msg, {}))

        handler.assert_not_awaited()
        self.assertIsNone(result)


class TestMiddlewareBackwardCompat(unittest.TestCase):
    """Backward compatibility: SubscriptionMiddleware still accepts premium_commands kwarg."""

    def test_init_with_empty_list(self):
        mw = SubscriptionMiddleware(premium_commands=[])
        self.assertIsNotNone(mw)

    def test_init_with_commands(self):
        mw = SubscriptionMiddleware(premium_commands=["cmd1"])
        self.assertIsNotNone(mw)

    def test_importable_from_package(self):
        from middlewares import SubscriptionMiddleware as SM
        self.assertTrue(callable(SM))


if __name__ == "__main__":
    unittest.main()
