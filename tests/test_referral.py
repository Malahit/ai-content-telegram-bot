"""
Unit tests for the referral system.

Tests cover:
- Referral code generation
- Referral link format
- /start with referral code processing
- Self-referral blocking
- Bonus posts crediting
- Referrer notification
- Middleware with bonus posts
- Referral stats
"""

import asyncio
import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

# Make sure the project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set required env vars before importing bot module
os.environ.setdefault("BOT_TOKEN", "123456:ABC-TEST-TOKEN")
os.environ.setdefault("PPLX_API_KEY", "test-pplx-key")

from aiogram.types import Message


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_message(text: str, user_id: int = 123, username: str = "testuser") -> MagicMock:
    """Return a minimal mock Message for testing."""
    msg = MagicMock()
    msg.__class__ = Message
    msg.text = text
    msg.from_user = MagicMock()
    msg.from_user.id = user_id
    msg.from_user.username = username
    msg.from_user.first_name = "Test"
    msg.from_user.last_name = "User"
    msg.answer = AsyncMock()
    msg.bot = MagicMock()
    msg.bot.send_message = AsyncMock()
    return msg


def _make_user(
    telegram_id: int = 123,
    username: str = "testuser",
    referral_code: str = None,
    referred_by: int = None,
    referral_bonus_posts: int = 0,
    referrals_count: int = 0,
):
    """Create a mock User object."""
    user = MagicMock()
    user.telegram_id = telegram_id
    user.username = username
    user.referral_code = referral_code
    user.referred_by = referred_by
    user.referral_bonus_posts = referral_bonus_posts
    user.referrals_count = referrals_count
    user.is_premium = False
    user.first_name = "Test"
    user.last_name = "User"
    return user


# ---------------------------------------------------------------------------
# Test: referral code generation
# ---------------------------------------------------------------------------


class TestGenerateReferralCode(unittest.TestCase):
    """Test referral code generation."""

    def test_generate_referral_code_returns_string(self):
        """generate_referral_code() returns a non-empty string."""
        from services.referral_service import generate_referral_code
        code = generate_referral_code()
        self.assertIsInstance(code, str)
        self.assertTrue(len(code) > 0)

    def test_generate_referral_code_is_url_safe(self):
        """Generated code contains only URL-safe characters."""
        import re
        from services.referral_service import generate_referral_code
        for _ in range(50):
            code = generate_referral_code()
            self.assertRegex(code, r'^[A-Za-z0-9_-]+$')

    def test_generate_referral_code_uniqueness(self):
        """Multiple calls produce different codes (probabilistically)."""
        from services.referral_service import generate_referral_code
        codes = {generate_referral_code() for _ in range(100)}
        # With 8-char URL-safe tokens, collisions in 100 are astronomically unlikely
        self.assertGreater(len(codes), 90)


# ---------------------------------------------------------------------------
# Test: referral link format
# ---------------------------------------------------------------------------


class TestReferralLinkFormat(unittest.TestCase):
    """Test referral link construction."""

    def test_referral_link_format(self):
        """Referral link follows the expected format."""
        from handlers.referral_handler import BOT_USERNAME
        code = "abc123XY"
        link = f"https://t.me/{BOT_USERNAME}?start=ref_{code}"
        self.assertEqual(link, "https://t.me/ai_content_helper_bot?start=ref_abc123XY")

    def test_referral_link_starts_with_ref_prefix(self):
        """Deep link argument starts with ref_ prefix."""
        code = "testcode"
        deep_link_arg = f"ref_{code}"
        self.assertTrue(deep_link_arg.startswith("ref_"))
        self.assertEqual(deep_link_arg[4:], code)


# ---------------------------------------------------------------------------
# Test: /start with referral code
# ---------------------------------------------------------------------------


class TestStartWithReferralCode(unittest.TestCase):
    """Test /start deep link referral processing."""

    def _run(self, coro):
        return asyncio.run(coro)

    @patch("bot.get_referral_stats", new_callable=AsyncMock)
    @patch("bot.credit_referral_bonus", new_callable=AsyncMock)
    @patch("bot.get_user_by_referral_code", new_callable=AsyncMock)
    @patch("bot.user_service")
    @patch("bot.resolve_user_and_tenant", new_callable=AsyncMock)
    @patch("bot.get_session")
    def test_new_user_with_valid_referral(
        self, mock_session, mock_resolve, mock_user_svc,
        mock_get_by_code, mock_credit, mock_ref_stats
    ):
        """New user joining via referral link triggers bonus crediting."""
        referrer = _make_user(telegram_id=999, referral_code="ABC123", referral_bonus_posts=0)
        mock_get_by_code.return_value = referrer
        mock_credit.return_value = True
        mock_user_svc.get_user = AsyncMock(return_value=None)  # new user
        mock_user_svc.register_or_get_user = AsyncMock(return_value=_make_user(telegram_id=123))
        mock_user_svc.is_user_banned = AsyncMock(return_value=False)
        mock_ref_stats.return_value = None

        # Mock session context manager
        mock_session.return_value.__aenter__ = AsyncMock()
        mock_session.return_value.__aexit__ = AsyncMock()

        from bot import start_handler

        msg = _make_message("/start ref_ABC123", user_id=123)
        command = MagicMock()
        command.args = "ref_ABC123"

        self._run(start_handler(msg, command))

        mock_get_by_code.assert_awaited_once_with("ABC123")
        mock_credit.assert_awaited_once_with(999, 123)


# ---------------------------------------------------------------------------
# Test: self-referral blocked
# ---------------------------------------------------------------------------


class TestSelfReferralBlocked(unittest.TestCase):
    """Self-referral should not credit bonus."""

    def _run(self, coro):
        return asyncio.run(coro)

    @patch("bot.get_referral_stats", new_callable=AsyncMock)
    @patch("bot.credit_referral_bonus", new_callable=AsyncMock)
    @patch("bot.get_user_by_referral_code", new_callable=AsyncMock)
    @patch("bot.user_service")
    @patch("bot.resolve_user_and_tenant", new_callable=AsyncMock)
    @patch("bot.get_session")
    def test_self_referral_not_credited(
        self, mock_session, mock_resolve, mock_user_svc,
        mock_get_by_code, mock_credit, mock_ref_stats
    ):
        """When user tries to refer themselves, no bonus is credited."""
        # Referrer is the same user
        referrer = _make_user(telegram_id=123, referral_code="SELF01")
        mock_get_by_code.return_value = referrer
        mock_user_svc.get_user = AsyncMock(return_value=None)  # new user
        mock_user_svc.register_or_get_user = AsyncMock(return_value=_make_user(telegram_id=123))
        mock_user_svc.is_user_banned = AsyncMock(return_value=False)
        mock_ref_stats.return_value = None

        mock_session.return_value.__aenter__ = AsyncMock()
        mock_session.return_value.__aexit__ = AsyncMock()

        from bot import start_handler

        msg = _make_message("/start ref_SELF01", user_id=123)
        command = MagicMock()
        command.args = "ref_SELF01"

        self._run(start_handler(msg, command))

        # credit_referral_bonus should NOT be called for self-referral
        mock_credit.assert_not_awaited()


# ---------------------------------------------------------------------------
# Test: bonus posts credited
# ---------------------------------------------------------------------------


class TestBonusPostsCredited(unittest.TestCase):
    """Test that referral bonus is correctly credited."""

    def _run(self, coro):
        return asyncio.run(coro)

    def test_referral_bonus_constant(self):
        """REFERRAL_BONUS_POSTS should be 2."""
        from services.referral_service import REFERRAL_BONUS_POSTS
        self.assertEqual(REFERRAL_BONUS_POSTS, 2)

    @patch("services.referral_service.AsyncSessionLocal")
    def test_credit_referral_bonus_updates_referrer(self, mock_session_cls):
        """credit_referral_bonus increments referrer's bonus and count."""
        referrer = _make_user(telegram_id=999, referral_bonus_posts=2, referrals_count=1)
        referred = _make_user(telegram_id=123)

        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()

        # First call returns referrer, second returns referred
        execute_results = [
            MagicMock(scalar_one_or_none=MagicMock(return_value=referrer)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=referred)),
        ]
        mock_session.execute = AsyncMock(side_effect=execute_results)
        mock_session.commit = AsyncMock()
        mock_session_cls.return_value = mock_session

        from services.referral_service import credit_referral_bonus
        result = self._run(credit_referral_bonus(999, 123))

        self.assertTrue(result)
        self.assertEqual(referrer.referral_bonus_posts, 4)  # 2 + 2
        self.assertEqual(referrer.referrals_count, 2)  # 1 + 1
        self.assertEqual(referred.referred_by, 999)


# ---------------------------------------------------------------------------
# Test: referrer notification
# ---------------------------------------------------------------------------


class TestReferrerNotification(unittest.TestCase):
    """Test that referrer is notified when a friend joins."""

    def _run(self, coro):
        return asyncio.run(coro)

    @patch("bot.get_referral_stats", new_callable=AsyncMock)
    @patch("bot.credit_referral_bonus", new_callable=AsyncMock)
    @patch("bot.get_user_by_referral_code", new_callable=AsyncMock)
    @patch("bot.user_service")
    @patch("bot.resolve_user_and_tenant", new_callable=AsyncMock)
    @patch("bot.get_session")
    def test_referrer_receives_notification(
        self, mock_session, mock_resolve, mock_user_svc,
        mock_get_by_code, mock_credit, mock_ref_stats
    ):
        """Referrer receives a notification message when friend joins."""
        referrer = _make_user(telegram_id=999, referral_code="XYZ789", referral_bonus_posts=4)
        mock_get_by_code.return_value = referrer
        mock_credit.return_value = True
        mock_user_svc.get_user = AsyncMock(return_value=None)
        mock_user_svc.register_or_get_user = AsyncMock(return_value=_make_user(telegram_id=456))
        mock_user_svc.is_user_banned = AsyncMock(return_value=False)
        mock_ref_stats.return_value = None

        mock_session.return_value.__aenter__ = AsyncMock()
        mock_session.return_value.__aexit__ = AsyncMock()

        from bot import start_handler

        msg = _make_message("/start ref_XYZ789", user_id=456)
        command = MagicMock()
        command.args = "ref_XYZ789"

        self._run(start_handler(msg, command))

        # Verify bot.send_message was called to notify the referrer
        msg.bot.send_message.assert_awaited_once()
        call_args = msg.bot.send_message.call_args
        self.assertEqual(call_args[0][0], 999)  # referrer's telegram_id
        self.assertIn("реферальной ссылке", call_args[0][1])


# ---------------------------------------------------------------------------
# Test: middleware with bonus posts
# ---------------------------------------------------------------------------


class TestMiddlewareWithBonusPosts(unittest.TestCase):
    """Test that SubscriptionMiddleware injects effective_daily_limit."""

    def _run(self, coro):
        return asyncio.run(coro)

    @patch("middlewares.subscription_middleware.get_user", new_callable=AsyncMock)
    def test_effective_limit_with_bonus(self, mock_get_user):
        """Middleware sets effective_daily_limit = FREE_DAILY_LIMIT + bonus."""
        user = _make_user(telegram_id=123, referral_bonus_posts=6)
        mock_get_user.return_value = user

        from middlewares.subscription_middleware import SubscriptionMiddleware, FREE_DAILY_LIMIT

        mw = SubscriptionMiddleware(premium_commands=[])
        handler = AsyncMock(return_value="ok")
        msg = _make_message("hello", user_id=123)
        data = {}

        self._run(mw(handler, msg, data))

        self.assertEqual(data["effective_daily_limit"], FREE_DAILY_LIMIT + 6)
        handler.assert_awaited_once()

    @patch("middlewares.subscription_middleware.get_user", new_callable=AsyncMock)
    def test_effective_limit_without_bonus(self, mock_get_user):
        """Middleware sets effective_daily_limit = FREE_DAILY_LIMIT when no bonus."""
        user = _make_user(telegram_id=123, referral_bonus_posts=0)
        mock_get_user.return_value = user

        from middlewares.subscription_middleware import SubscriptionMiddleware, FREE_DAILY_LIMIT

        mw = SubscriptionMiddleware(premium_commands=[])
        handler = AsyncMock(return_value="ok")
        msg = _make_message("test", user_id=123)
        data = {}

        self._run(mw(handler, msg, data))

        self.assertEqual(data["effective_daily_limit"], FREE_DAILY_LIMIT)

    @patch("middlewares.subscription_middleware.get_user", new_callable=AsyncMock)
    def test_effective_limit_for_unknown_user(self, mock_get_user):
        """Middleware defaults to FREE_DAILY_LIMIT for unknown users."""
        mock_get_user.return_value = None

        from middlewares.subscription_middleware import SubscriptionMiddleware, FREE_DAILY_LIMIT

        mw = SubscriptionMiddleware(premium_commands=[])
        handler = AsyncMock(return_value="ok")
        msg = _make_message("/start", user_id=999)
        data = {}

        self._run(mw(handler, msg, data))

        self.assertEqual(data["effective_daily_limit"], FREE_DAILY_LIMIT)


# ---------------------------------------------------------------------------
# Test: referral stats
# ---------------------------------------------------------------------------


class TestReferralStats(unittest.TestCase):
    """Test referral stats retrieval."""

    def _run(self, coro):
        return asyncio.run(coro)

    @patch("services.referral_service.AsyncSessionLocal")
    def test_get_referral_stats_returns_correct_data(self, mock_session_cls):
        """get_referral_stats returns dict with code, count, and bonus."""
        user = _make_user(
            telegram_id=123,
            referral_code="TEST01",
            referrals_count=5,
            referral_bonus_posts=10,
        )

        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()
        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=user))
        )
        mock_session_cls.return_value = mock_session

        from services.referral_service import get_referral_stats
        stats = self._run(get_referral_stats(123))

        self.assertIsNotNone(stats)
        self.assertEqual(stats["referral_code"], "TEST01")
        self.assertEqual(stats["referrals_count"], 5)
        self.assertEqual(stats["bonus_posts"], 10)

    @patch("services.referral_service.AsyncSessionLocal")
    def test_get_referral_stats_returns_none_for_unknown_user(self, mock_session_cls):
        """get_referral_stats returns None for non-existent user."""
        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()
        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
        )
        mock_session_cls.return_value = mock_session

        from services.referral_service import get_referral_stats
        stats = self._run(get_referral_stats(999))

        self.assertIsNone(stats)


if __name__ == "__main__":
    unittest.main()
