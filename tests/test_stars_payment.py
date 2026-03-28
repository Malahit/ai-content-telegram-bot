"""
Unit tests for Telegram Stars payment flow (Sprint 1 monetization).

Tests:
1. /subscribe shows plans for non-premium users
2. /subscribe shows active status for premium users
3. Plan selection sends correct Stars invoice
4. Monthly plan includes subscription_period for recurring
5. Pre-checkout is approved
6. Successful payment activates subscription and records payment
7. /status shows correct info for free and premium users
"""

import asyncio
import os
import sys
import unittest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Ensure dummy env vars exist so config doesn't crash on import
os.environ.setdefault("BOT_TOKEN", "123456:ABCdefGhIjKlMnOpQrStUvWxYz")
os.environ.setdefault("PPLX_API_KEY", "test-key")

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from database.models import Base, User, Payment, PaymentStatus


class TestStarsSubscribeCommand(unittest.TestCase):
    """Test /subscribe command handler."""

    def _run(self, coro):
        return asyncio.run(coro)

    @patch("handlers.subscription.payments_enabled", return_value=True)
    @patch("handlers.subscription.check_is_premium", new_callable=AsyncMock)
    def test_subscribe_shows_plans_for_free_user(self, mock_premium, mock_payments):
        mock_premium.return_value = False

        from handlers.subscription import subscribe_command

        msg = AsyncMock()
        msg.from_user = MagicMock()
        msg.from_user.id = 123
        msg.answer = AsyncMock()

        self._run(subscribe_command(msg))

        msg.answer.assert_awaited_once()
        call_args = msg.answer.call_args
        text = call_args[0][0] if call_args[0] else call_args[1].get("text", "")
        self.assertIn("Pro подписка", text)
        # Should have inline keyboard with plans
        reply_markup = call_args[1].get("reply_markup")
        self.assertIsNotNone(reply_markup)

    @patch("handlers.subscription.payments_enabled", return_value=True)
    @patch("handlers.subscription.get_user", new_callable=AsyncMock)
    @patch("handlers.subscription.check_is_premium", new_callable=AsyncMock)
    def test_subscribe_shows_active_for_premium_user(self, mock_premium, mock_get_user, mock_payments):
        mock_premium.return_value = True
        mock_user = MagicMock()
        mock_user.subscription_end = datetime.utcnow() + timedelta(days=15)
        mock_get_user.return_value = mock_user

        from handlers.subscription import subscribe_command

        msg = AsyncMock()
        msg.from_user = MagicMock()
        msg.from_user.id = 123
        msg.answer = AsyncMock()

        self._run(subscribe_command(msg))

        msg.answer.assert_awaited_once()
        text = msg.answer.call_args[0][0]
        self.assertIn("уже есть активная подписка", text)

    @patch("handlers.subscription.payments_enabled", return_value=False)
    def test_subscribe_disabled_shows_message(self, mock_payments):
        from handlers.subscription import subscribe_command

        msg = AsyncMock()
        msg.from_user = MagicMock()
        msg.from_user.id = 123
        msg.answer = AsyncMock()

        self._run(subscribe_command(msg))

        msg.answer.assert_awaited_once()
        text = msg.answer.call_args[0][0]
        self.assertIn("отключены", text)


class TestStarsInvoice(unittest.TestCase):
    """Test plan callback sends correct invoice."""

    def _run(self, coro):
        return asyncio.run(coro)

    @patch("handlers.subscription.register_or_get_user", new_callable=AsyncMock)
    @patch("handlers.subscription.payments_enabled", return_value=True)
    def test_week_plan_sends_one_time_invoice(self, mock_payments, mock_register):
        mock_register.return_value = MagicMock()
        from handlers.subscription import subscription_callback

        cb = AsyncMock()
        cb.data = "pro_week"
        cb.from_user = MagicMock()
        cb.from_user.id = 42
        cb.from_user.username = "test"
        cb.from_user.first_name = "Test"
        cb.from_user.last_name = "User"
        cb.answer = AsyncMock()
        cb.message = AsyncMock()
        cb.message.answer_invoice = AsyncMock()
        cb.message.answer = AsyncMock()

        self._run(subscription_callback(cb))

        cb.message.answer_invoice.assert_awaited_once()
        kwargs = cb.message.answer_invoice.call_args[1]
        self.assertEqual(kwargs["currency"], "XTR")
        self.assertEqual(kwargs["prices"][0].amount, 25)
        self.assertEqual(kwargs["payload"], "pro_week")
        self.assertNotIn("subscription_period", kwargs)

    @patch("handlers.subscription.register_or_get_user", new_callable=AsyncMock)
    @patch("handlers.subscription.payments_enabled", return_value=True)
    def test_month_plan_sends_recurring_invoice(self, mock_payments, mock_register):
        mock_register.return_value = MagicMock()
        from handlers.subscription import subscription_callback

        cb = AsyncMock()
        cb.data = "pro_month"
        cb.from_user = MagicMock()
        cb.from_user.id = 42
        cb.from_user.username = "test"
        cb.from_user.first_name = "Test"
        cb.from_user.last_name = "User"
        cb.answer = AsyncMock()
        cb.message = AsyncMock()
        cb.message.answer_invoice = AsyncMock()
        cb.message.answer = AsyncMock()

        self._run(subscription_callback(cb))

        cb.message.answer_invoice.assert_awaited_once()
        kwargs = cb.message.answer_invoice.call_args[1]
        self.assertEqual(kwargs["currency"], "XTR")
        self.assertEqual(kwargs["prices"][0].amount, 75)
        self.assertEqual(kwargs["subscription_period"], 2592000)

    @patch("handlers.subscription.register_or_get_user", new_callable=AsyncMock)
    @patch("handlers.subscription.payments_enabled", return_value=True)
    def test_year_plan_correct_stars(self, mock_payments, mock_register):
        mock_register.return_value = MagicMock()
        from handlers.subscription import subscription_callback

        cb = AsyncMock()
        cb.data = "pro_year"
        cb.from_user = MagicMock()
        cb.from_user.id = 42
        cb.from_user.username = "test"
        cb.from_user.first_name = "Test"
        cb.from_user.last_name = "User"
        cb.answer = AsyncMock()
        cb.message = AsyncMock()
        cb.message.answer_invoice = AsyncMock()
        cb.message.answer = AsyncMock()

        self._run(subscription_callback(cb))

        kwargs = cb.message.answer_invoice.call_args[1]
        self.assertEqual(kwargs["prices"][0].amount, 600)
        self.assertEqual(kwargs["payload"], "pro_year")


class TestPreCheckout(unittest.TestCase):
    """Test pre-checkout handler."""

    def _run(self, coro):
        return asyncio.run(coro)

    @patch("handlers.subscription.payments_enabled", return_value=True)
    def test_pre_checkout_approved(self, mock_payments):
        from handlers.subscription import pre_checkout_handler

        query = AsyncMock()
        query.from_user = MagicMock()
        query.from_user.id = 42
        query.invoice_payload = "pro_week"
        query.answer = AsyncMock()

        self._run(pre_checkout_handler(query))

        query.answer.assert_awaited_once_with(ok=True)

    @patch("handlers.subscription.payments_enabled", return_value=False)
    def test_pre_checkout_rejected_when_disabled(self, mock_payments):
        from handlers.subscription import pre_checkout_handler

        query = AsyncMock()
        query.from_user = MagicMock()
        query.from_user.id = 42
        query.answer = AsyncMock()

        self._run(pre_checkout_handler(query))

        query.answer.assert_awaited_once()
        kwargs = query.answer.call_args[1]
        self.assertFalse(kwargs["ok"])


class TestSuccessfulPayment(unittest.TestCase):
    """Test successful payment activates subscription."""

    @classmethod
    def setUpClass(cls):
        cls.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            echo=False,
        )
        cls.SessionLocal = async_sessionmaker(
            cls.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    def setUp(self):
        asyncio.run(self._setup_db())

    async def _setup_db(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    def tearDown(self):
        asyncio.run(self._teardown_db())

    async def _teardown_db(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    def _run(self, coro):
        return asyncio.run(coro)

    def test_successful_payment_activates_pro(self):
        async def _test():
            import handlers.subscription as hs
            original_session = hs.AsyncSessionLocal
            hs.AsyncSessionLocal = self.SessionLocal

            try:
                # Create user first
                async with self.SessionLocal() as session:
                    user = User(
                        telegram_id=42,
                        username="testuser",
                        first_name="Test",
                        is_premium=False,
                    )
                    session.add(user)
                    await session.commit()

                # Mock successful payment message
                msg = AsyncMock()
                msg.from_user = MagicMock()
                msg.from_user.id = 42
                msg.from_user.username = "testuser"
                msg.from_user.first_name = "Test"
                msg.from_user.last_name = None
                msg.answer = AsyncMock()

                payment_info = MagicMock()
                payment_info.invoice_payload = "pro_week"
                payment_info.telegram_payment_charge_id = "charge_123"
                msg.successful_payment = payment_info

                await hs.successful_payment_handler(msg)

                # Verify user is now premium
                from sqlalchemy import select
                async with self.SessionLocal() as session:
                    result = await session.execute(
                        select(User).where(User.telegram_id == 42)
                    )
                    user = result.scalar_one()
                    self.assertTrue(user.is_premium)
                    self.assertIsNotNone(user.subscription_end)
                    # Week plan = 7 days
                    days_left = (user.subscription_end - datetime.utcnow()).days
                    self.assertGreaterEqual(days_left, 6)
                    self.assertLessEqual(days_left, 7)

                # Verify payment record
                async with self.SessionLocal() as session:
                    result = await session.execute(select(Payment))
                    payments = result.scalars().all()
                    self.assertEqual(len(payments), 1)
                    self.assertEqual(payments[0].amount, 25)
                    self.assertEqual(payments[0].currency, "XTR")
                    self.assertEqual(payments[0].status, PaymentStatus.SUCCESS)
                    self.assertEqual(payments[0].provider, "telegram_stars")

                # Verify confirmation message
                msg.answer.assert_awaited_once()
                text = msg.answer.call_args[0][0]
                self.assertIn("Подписка Pro активирована", text)
                self.assertIn("Пробная неделя", text)

            finally:
                hs.AsyncSessionLocal = original_session

        self._run(_test())

    def test_payment_extends_existing_subscription(self):
        async def _test():
            import handlers.subscription as hs
            original_session = hs.AsyncSessionLocal
            hs.AsyncSessionLocal = self.SessionLocal

            try:
                # Create user with existing subscription
                future_date = datetime.utcnow() + timedelta(days=10)
                async with self.SessionLocal() as session:
                    user = User(
                        telegram_id=99,
                        username="prouser",
                        is_premium=True,
                        subscription_end=future_date,
                    )
                    session.add(user)
                    await session.commit()

                msg = AsyncMock()
                msg.from_user = MagicMock()
                msg.from_user.id = 99
                msg.from_user.username = "prouser"
                msg.from_user.first_name = "Pro"
                msg.from_user.last_name = None
                msg.answer = AsyncMock()

                payment_info = MagicMock()
                payment_info.invoice_payload = "pro_month"
                payment_info.telegram_payment_charge_id = "charge_456"
                msg.successful_payment = payment_info

                await hs.successful_payment_handler(msg)

                from sqlalchemy import select
                async with self.SessionLocal() as session:
                    result = await session.execute(
                        select(User).where(User.telegram_id == 99)
                    )
                    user = result.scalar_one()
                    # Should extend from existing end date: 10 + 30 = ~40 days
                    days_left = (user.subscription_end - datetime.utcnow()).days
                    self.assertGreaterEqual(days_left, 38)
                    self.assertLessEqual(days_left, 40)

            finally:
                hs.AsyncSessionLocal = original_session

        self._run(_test())


class TestStatusCommand(unittest.TestCase):
    """Test /status shows correct subscription info."""

    def _run(self, coro):
        return asyncio.run(coro)

    @patch("handlers.subscription.get_total_post_count", new_callable=AsyncMock)
    @patch("handlers.subscription.get_today_post_count", new_callable=AsyncMock)
    @patch("handlers.subscription.check_is_premium", new_callable=AsyncMock)
    @patch("handlers.subscription.get_user", new_callable=AsyncMock)
    def test_status_free_user(self, mock_get_user, mock_premium, mock_today, mock_total):
        mock_get_user.return_value = MagicMock(is_premium=False, subscription_end=None)
        mock_premium.return_value = False
        mock_today.return_value = 2
        mock_total.return_value = 47

        from handlers.subscription import status_command

        msg = AsyncMock()
        msg.from_user = MagicMock()
        msg.from_user.id = 123
        msg.answer = AsyncMock()

        self._run(status_command(msg))

        msg.answer.assert_awaited_once()
        text = msg.answer.call_args[0][0]
        self.assertIn("Free", text)
        self.assertIn("2/3", text)
        self.assertIn("sonar-small", text)
        self.assertIn("47", text)

    @patch("handlers.subscription.get_total_post_count", new_callable=AsyncMock)
    @patch("handlers.subscription.get_today_post_count", new_callable=AsyncMock)
    @patch("handlers.subscription.check_is_premium", new_callable=AsyncMock)
    @patch("handlers.subscription.get_user", new_callable=AsyncMock)
    def test_status_premium_user(self, mock_get_user, mock_premium, mock_today, mock_total):
        expiry = datetime.utcnow() + timedelta(days=15)
        mock_user = MagicMock(is_premium=True, subscription_end=expiry)
        mock_get_user.return_value = mock_user
        mock_premium.return_value = True
        mock_today.return_value = 5
        mock_total.return_value = 100

        from handlers.subscription import status_command

        msg = AsyncMock()
        msg.from_user = MagicMock()
        msg.from_user.id = 123
        msg.answer = AsyncMock()

        self._run(status_command(msg))

        msg.answer.assert_awaited_once()
        text = msg.answer.call_args[0][0]
        self.assertIn("Pro", text)
        self.assertIn("5/30", text)
        self.assertIn("sonar-pro", text)
        self.assertIn("100", text)


if __name__ == "__main__":
    unittest.main()
