"""
Unit tests for autopost service module.

Tests subscription CRUD, due-subscription logic, and deactivation.
"""

import asyncio
import unittest
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from database.models import Base, AutopostSubscription
from services.autopost_service import (
    AUTOPOST_PLANS,
    create_autopost_subscription,
    get_active_subscriptions,
    get_due_subscriptions,
    deactivate_expired_subscriptions,
    cancel_subscription,
    update_topic,
    update_last_post,
    _is_due,
)


class TestAutopostService(unittest.TestCase):
    """Test cases for autopost service functions."""

    @classmethod
    def setUpClass(cls):
        cls.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:", echo=False
        )
        cls.SessionLocal = async_sessionmaker(
            cls.engine, class_=AsyncSession, expire_on_commit=False
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

    def test_create_subscription(self):
        """Test creating a new autopost subscription."""

        async def _test():
            async with self.SessionLocal() as session:
                sub = await create_autopost_subscription(
                    session=session,
                    telegram_id=123456789,
                    channel_id="-100123456",
                    channel_title="Test Channel",
                    topic="здоровое питание",
                    frequency="daily",
                    send_hour_utc=6,
                    send_hour_local=9,
                    plan_type="month",
                    stars_paid=150,
                    telegram_charge_id="charge_123",
                )

            self.assertIsNotNone(sub)
            self.assertEqual(sub.telegram_id, 123456789)
            self.assertEqual(sub.channel_id, "-100123456")
            self.assertEqual(sub.topic, "здоровое питание")
            self.assertEqual(sub.frequency, "daily")
            self.assertEqual(sub.send_hour_utc, 6)
            self.assertEqual(sub.plan_type, "month")
            self.assertEqual(sub.stars_paid, 150)
            self.assertTrue(sub.is_active)
            self.assertIsNotNone(sub.expires_at)
            # expires_at should be ~30 days from now
            expires = sub.expires_at
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
            delta = (expires - datetime.now(timezone.utc)).days
            self.assertGreaterEqual(delta, 29)
            self.assertLessEqual(delta, 31)

        asyncio.run(_test())

    def test_get_active_subscriptions(self):
        """Test retrieving active subscriptions for a user."""

        async def _test():
            async with self.SessionLocal() as session:
                await create_autopost_subscription(
                    session=session,
                    telegram_id=111,
                    channel_id="-100111",
                    channel_title="Ch1",
                    topic="topic1",
                    frequency="daily",
                    send_hour_utc=8,
                    send_hour_local=11,
                    plan_type="month",
                    stars_paid=150,
                )
                await create_autopost_subscription(
                    session=session,
                    telegram_id=111,
                    channel_id="-100222",
                    channel_title="Ch2",
                    topic="topic2",
                    frequency="weekly",
                    send_hour_utc=12,
                    send_hour_local=15,
                    plan_type="half_year",
                    stars_paid=750,
                )
                # Different user
                await create_autopost_subscription(
                    session=session,
                    telegram_id=222,
                    channel_id="-100333",
                    channel_title="Ch3",
                    topic="topic3",
                    frequency="daily",
                    send_hour_utc=8,
                    send_hour_local=11,
                    plan_type="month",
                    stars_paid=150,
                )

            async with self.SessionLocal() as session:
                subs = await get_active_subscriptions(session, 111)
            self.assertEqual(len(subs), 2)

            async with self.SessionLocal() as session:
                subs = await get_active_subscriptions(session, 222)
            self.assertEqual(len(subs), 1)

            async with self.SessionLocal() as session:
                subs = await get_active_subscriptions(session, 999)
            self.assertEqual(len(subs), 0)

        asyncio.run(_test())

    def test_deactivate_expired(self):
        """Test deactivation of expired subscriptions."""

        async def _test():
            async with self.SessionLocal() as session:
                # Create an expired subscription
                sub = AutopostSubscription(
                    telegram_id=111,
                    channel_id="-100111",
                    topic="expired topic",
                    frequency="daily",
                    send_hour_utc=8,
                    send_hour_local=11,
                    plan_type="month",
                    stars_paid=150,
                    is_active=True,
                    expires_at=datetime.now(timezone.utc) - timedelta(days=1),
                )
                session.add(sub)
                await session.commit()

            async with self.SessionLocal() as session:
                count = await deactivate_expired_subscriptions(session)
            self.assertEqual(count, 1)

            async with self.SessionLocal() as session:
                subs = await get_active_subscriptions(session, 111)
            self.assertEqual(len(subs), 0)

        asyncio.run(_test())

    def test_cancel_subscription(self):
        """Test subscription cancellation."""

        async def _test():
            async with self.SessionLocal() as session:
                sub = await create_autopost_subscription(
                    session=session,
                    telegram_id=111,
                    channel_id="-100111",
                    channel_title="Ch1",
                    topic="cancel me",
                    frequency="daily",
                    send_hour_utc=8,
                    send_hour_local=11,
                    plan_type="month",
                    stars_paid=150,
                )
                sub_id = sub.id

            async with self.SessionLocal() as session:
                ok = await cancel_subscription(session, sub_id, 111)
            self.assertTrue(ok)

            async with self.SessionLocal() as session:
                subs = await get_active_subscriptions(session, 111)
            self.assertEqual(len(subs), 0)

            # Wrong user
            async with self.SessionLocal() as session:
                ok = await cancel_subscription(session, sub_id, 999)
            self.assertFalse(ok)

        asyncio.run(_test())

    def test_update_topic(self):
        """Test updating subscription topic."""

        async def _test():
            async with self.SessionLocal() as session:
                sub = await create_autopost_subscription(
                    session=session,
                    telegram_id=111,
                    channel_id="-100111",
                    channel_title="Ch1",
                    topic="old topic",
                    frequency="daily",
                    send_hour_utc=8,
                    send_hour_local=11,
                    plan_type="month",
                    stars_paid=150,
                )
                sub_id = sub.id

            async with self.SessionLocal() as session:
                ok = await update_topic(session, sub_id, 111, "new topic")
            self.assertTrue(ok)

            async with self.SessionLocal() as session:
                subs = await get_active_subscriptions(session, 111)
            self.assertEqual(subs[0].topic, "new topic")

        asyncio.run(_test())


class TestIsDueLogic(unittest.TestCase):
    """Test the _is_due helper function."""

    def _make_sub(self, frequency, send_hour_utc, last_post_at=None):
        sub = AutopostSubscription(
            telegram_id=1,
            channel_id="-1",
            topic="test",
            frequency=frequency,
            send_hour_utc=send_hour_utc,
            send_hour_local=send_hour_utc + 3,
            plan_type="month",
            stars_paid=150,
            is_active=True,
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            last_post_at=last_post_at,
        )
        return sub

    def test_daily_right_hour_no_post(self):
        sub = self._make_sub("daily", 8)
        now = datetime(2026, 3, 28, 8, 30, tzinfo=timezone.utc)
        self.assertTrue(_is_due(sub, now, 8))

    def test_daily_wrong_hour(self):
        sub = self._make_sub("daily", 8)
        now = datetime(2026, 3, 28, 10, 0, tzinfo=timezone.utc)
        self.assertFalse(_is_due(sub, now, 10))

    def test_daily_already_posted_today(self):
        posted = datetime(2026, 3, 28, 8, 0, tzinfo=timezone.utc)
        sub = self._make_sub("daily", 8, last_post_at=posted)
        now = datetime(2026, 3, 28, 8, 30, tzinfo=timezone.utc)
        self.assertFalse(_is_due(sub, now, 8))

    def test_twice_daily_first_slot(self):
        sub = self._make_sub("twice_daily", 6)
        now = datetime(2026, 3, 28, 6, 0, tzinfo=timezone.utc)
        self.assertTrue(_is_due(sub, now, 6))

    def test_twice_daily_second_slot(self):
        sub = self._make_sub("twice_daily", 6)
        now = datetime(2026, 3, 28, 18, 0, tzinfo=timezone.utc)
        self.assertTrue(_is_due(sub, now, 18))

    def test_twice_daily_too_soon(self):
        posted = datetime(2026, 3, 28, 6, 0, tzinfo=timezone.utc)
        sub = self._make_sub("twice_daily", 6, last_post_at=posted)
        now = datetime(2026, 3, 28, 6, 30, tzinfo=timezone.utc)
        self.assertFalse(_is_due(sub, now, 6))

    def test_every_6h_valid_slot(self):
        sub = self._make_sub("every_6h", 0)
        now = datetime(2026, 3, 28, 12, 0, tzinfo=timezone.utc)
        self.assertTrue(_is_due(sub, now, 12))

    def test_every_6h_invalid_slot(self):
        sub = self._make_sub("every_6h", 0)
        now = datetime(2026, 3, 28, 3, 0, tzinfo=timezone.utc)
        self.assertFalse(_is_due(sub, now, 3))

    def test_weekly_no_post(self):
        sub = self._make_sub("weekly", 10)
        now = datetime(2026, 3, 28, 10, 0, tzinfo=timezone.utc)
        self.assertTrue(_is_due(sub, now, 10))

    def test_weekly_too_recent(self):
        posted = datetime(2026, 3, 25, 10, 0, tzinfo=timezone.utc)
        sub = self._make_sub("weekly", 10, last_post_at=posted)
        now = datetime(2026, 3, 28, 10, 0, tzinfo=timezone.utc)
        self.assertFalse(_is_due(sub, now, 10))

    def test_weekly_overdue(self):
        posted = datetime(2026, 3, 20, 10, 0, tzinfo=timezone.utc)
        sub = self._make_sub("weekly", 10, last_post_at=posted)
        now = datetime(2026, 3, 28, 10, 0, tzinfo=timezone.utc)
        self.assertTrue(_is_due(sub, now, 10))


class TestGetDueSubscriptions(unittest.TestCase):
    """Test get_due_subscriptions with real DB."""

    @classmethod
    def setUpClass(cls):
        cls.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:", echo=False
        )
        cls.SessionLocal = async_sessionmaker(
            cls.engine, class_=AsyncSession, expire_on_commit=False
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

    def test_get_due_daily(self):
        """Test that a daily subscription is returned when due."""

        async def _test():
            now = datetime.now(timezone.utc)
            async with self.SessionLocal() as session:
                sub = AutopostSubscription(
                    telegram_id=111,
                    channel_id="-100111",
                    topic="daily test",
                    frequency="daily",
                    send_hour_utc=now.hour,
                    send_hour_local=now.hour + 3,
                    plan_type="month",
                    stars_paid=150,
                    is_active=True,
                    expires_at=now + timedelta(days=30),
                    last_post_at=None,
                )
                session.add(sub)
                await session.commit()

            async with self.SessionLocal() as session:
                due = await get_due_subscriptions(session)
            self.assertEqual(len(due), 1)
            self.assertEqual(due[0].topic, "daily test")

        asyncio.run(_test())

    def test_expired_not_returned(self):
        """Test that expired subscriptions are not in due list."""

        async def _test():
            now = datetime.now(timezone.utc)
            async with self.SessionLocal() as session:
                sub = AutopostSubscription(
                    telegram_id=111,
                    channel_id="-100111",
                    topic="expired",
                    frequency="daily",
                    send_hour_utc=now.hour,
                    send_hour_local=now.hour + 3,
                    plan_type="month",
                    stars_paid=150,
                    is_active=True,
                    expires_at=now - timedelta(days=1),
                    last_post_at=None,
                )
                session.add(sub)
                await session.commit()

            async with self.SessionLocal() as session:
                due = await get_due_subscriptions(session)
            self.assertEqual(len(due), 0)

        asyncio.run(_test())


class TestAutopostPlans(unittest.TestCase):
    """Test plan configuration."""

    def test_plans_exist(self):
        self.assertIn("month", AUTOPOST_PLANS)
        self.assertIn("half_year", AUTOPOST_PLANS)
        self.assertIn("year", AUTOPOST_PLANS)

    def test_plan_values(self):
        self.assertEqual(AUTOPOST_PLANS["month"]["stars"], 150)
        self.assertEqual(AUTOPOST_PLANS["half_year"]["stars"], 750)
        self.assertEqual(AUTOPOST_PLANS["year"]["stars"], 1200)
        self.assertEqual(AUTOPOST_PLANS["month"]["days"], 30)
        self.assertEqual(AUTOPOST_PLANS["half_year"]["days"], 180)
        self.assertEqual(AUTOPOST_PLANS["year"]["days"], 365)


if __name__ == "__main__":
    unittest.main()
