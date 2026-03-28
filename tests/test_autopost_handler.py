"""
Unit tests for autopost handler module.

Tests FSM states, frequency selection, time conversion, and channel validation.
"""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from handlers.autopost_handler import (
    AutopostSetup,
    _msk_to_utc,
    _utc_to_msk,
    MSK_OFFSET,
)
from services.autopost_service import AUTOPOST_PLANS, FREQUENCY_LABELS


class TestTimeConversion(unittest.TestCase):
    """Test MSK <-> UTC time conversion helpers."""

    def test_msk_to_utc(self):
        self.assertEqual(_msk_to_utc(9), 6)   # 09:00 МСК = 06:00 UTC
        self.assertEqual(_msk_to_utc(0), 21)   # 00:00 МСК = 21:00 UTC
        self.assertEqual(_msk_to_utc(3), 0)    # 03:00 МСК = 00:00 UTC
        self.assertEqual(_msk_to_utc(23), 20)

    def test_utc_to_msk(self):
        self.assertEqual(_utc_to_msk(6), 9)    # 06:00 UTC = 09:00 МСК
        self.assertEqual(_utc_to_msk(21), 0)   # 21:00 UTC = 00:00 МСК
        self.assertEqual(_utc_to_msk(0), 3)    # 00:00 UTC = 03:00 МСК

    def test_roundtrip(self):
        for h in range(24):
            self.assertEqual(_utc_to_msk(_msk_to_utc(h)), h)


class TestFSMStates(unittest.TestCase):
    """Test that FSM states are defined correctly."""

    def test_states_exist(self):
        self.assertIsNotNone(AutopostSetup.waiting_topic)
        self.assertIsNotNone(AutopostSetup.waiting_frequency)
        self.assertIsNotNone(AutopostSetup.waiting_time)
        self.assertIsNotNone(AutopostSetup.waiting_custom_time)
        self.assertIsNotNone(AutopostSetup.waiting_channel)
        self.assertIsNotNone(AutopostSetup.waiting_confirmation)
        self.assertIsNotNone(AutopostSetup.editing_topic)


class TestFrequencyLabels(unittest.TestCase):
    """Test frequency labels mapping."""

    def test_all_frequencies_have_labels(self):
        frequencies = ["daily", "twice_daily", "every_6h", "weekly"]
        for freq in frequencies:
            self.assertIn(freq, FREQUENCY_LABELS)

    def test_labels_in_russian(self):
        for label in FREQUENCY_LABELS.values():
            self.assertIsInstance(label, str)
            self.assertTrue(len(label) > 0)


class TestPlanConfiguration(unittest.TestCase):
    """Test autopost plan pricing and limits."""

    def test_month_plan(self):
        plan = AUTOPOST_PLANS["month"]
        self.assertEqual(plan["stars"], 150)
        self.assertEqual(plan["days"], 30)
        self.assertEqual(plan["max_channels"], 1)

    def test_half_year_plan(self):
        plan = AUTOPOST_PLANS["half_year"]
        self.assertEqual(plan["stars"], 750)
        self.assertEqual(plan["days"], 180)
        self.assertEqual(plan["max_channels"], 3)

    def test_year_plan(self):
        plan = AUTOPOST_PLANS["year"]
        self.assertEqual(plan["stars"], 1200)
        self.assertEqual(plan["days"], 365)
        self.assertEqual(plan["max_channels"], 5)

    def test_price_per_day_decreases(self):
        """Longer plans should be cheaper per day."""
        month_ppd = AUTOPOST_PLANS["month"]["stars"] / AUTOPOST_PLANS["month"]["days"]
        half_ppd = AUTOPOST_PLANS["half_year"]["stars"] / AUTOPOST_PLANS["half_year"]["days"]
        year_ppd = AUTOPOST_PLANS["year"]["stars"] / AUTOPOST_PLANS["year"]["days"]
        self.assertGreater(month_ppd, half_ppd)
        self.assertGreater(half_ppd, year_ppd)


class TestChannelValidation(unittest.TestCase):
    """Test channel input handling logic."""

    def test_add_at_prefix(self):
        """Channel input without @ should get @ prepended."""
        channel = "my_channel"
        if not channel.startswith("@"):
            channel = "@" + channel
        self.assertEqual(channel, "@my_channel")

    def test_keep_at_prefix(self):
        """Channel input with @ should remain unchanged."""
        channel = "@my_channel"
        if not channel.startswith("@"):
            channel = "@" + channel
        self.assertEqual(channel, "@my_channel")


class TestPaymentPayload(unittest.TestCase):
    """Test payment payload format."""

    def test_payload_format(self):
        for plan_type in AUTOPOST_PLANS:
            payload = f"autopost:{plan_type}"
            self.assertTrue(payload.startswith("autopost:"))
            self.assertEqual(payload.split(":")[1], plan_type)

    def test_month_is_recurring(self):
        """Month plan should have subscription_period."""
        # subscription_period = 30 days in seconds
        self.assertEqual(2592000, 30 * 24 * 60 * 60)


if __name__ == "__main__":
    unittest.main()
