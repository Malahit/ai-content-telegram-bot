"""
Tests for polling manager functionality.

Tests the retry logic and exponential backoff for handling Telegram conflicts.
"""

import os
import sys
import unittest
import asyncio
from unittest.mock import Mock, AsyncMock, patch

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.polling_manager import PollingManager
from aiogram.exceptions import TelegramConflictError


class TestPollingManager(unittest.TestCase):
    """Test cases for PollingManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.manager = PollingManager(
            max_retries=3,
            initial_delay=0.1,  # Small delay for faster tests
            max_delay=1.0,
            backoff_factor=2.0
        )
    
    def test_initialization(self):
        """Test PollingManager initialization."""
        self.assertEqual(self.manager.max_retries, 3)
        self.assertEqual(self.manager.initial_delay, 0.1)
        self.assertEqual(self.manager.max_delay, 1.0)
        self.assertEqual(self.manager.backoff_factor, 2.0)
    
    def test_successful_polling(self):
        """Test polling that succeeds on first attempt."""
        # Create mock dispatcher and bot
        mock_dp = Mock()
        mock_bot = Mock()
        
        # Mock start_polling to succeed immediately
        async def mock_start_polling(bot):
            return None
        
        mock_dp.start_polling = AsyncMock(side_effect=mock_start_polling)
        
        # Run polling
        asyncio.run(self.manager.start_polling_with_retry(mock_dp, mock_bot))
        
        # start_polling should be called once
        self.assertEqual(mock_dp.start_polling.call_count, 1)
    
    def test_retry_on_conflict_error(self):
        """Test that polling retries on TelegramConflictError."""
        mock_dp = Mock()
        mock_bot = Mock()
        
        # Track call count
        call_count = 0
        
        async def mock_start_polling(bot):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise TelegramConflictError(method=Mock(), message="Conflict")
            return None
        
        mock_dp.start_polling = AsyncMock(side_effect=mock_start_polling)
        
        # Run polling
        asyncio.run(self.manager.start_polling_with_retry(mock_dp, mock_bot))
        
        # Should have retried and succeeded on third attempt
        self.assertEqual(call_count, 3)
    
    def test_max_retries_exceeded(self):
        """Test that max retries limit is respected."""
        mock_dp = Mock()
        mock_bot = Mock()
        
        # Always raise conflict error
        async def mock_start_polling(bot):
            raise TelegramConflictError(method=Mock(), message="Conflict")
        
        mock_dp.start_polling = AsyncMock(side_effect=mock_start_polling)
        
        # Should raise after max retries
        with self.assertRaises(TelegramConflictError):
            asyncio.run(self.manager.start_polling_with_retry(mock_dp, mock_bot))
        
        # Should have tried max_retries + 1 times (initial + retries)
        self.assertEqual(mock_dp.start_polling.call_count, 4)
    
    def test_conflict_callback_execution(self):
        """Test that conflict callback is executed on conflicts."""
        mock_dp = Mock()
        mock_bot = Mock()
        callback_executed = []
        
        def conflict_callback():
            callback_executed.append(True)
        
        call_count = 0
        
        async def mock_start_polling(bot):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise TelegramConflictError(method=Mock(), message="Conflict")
            return None
        
        mock_dp.start_polling = AsyncMock(side_effect=mock_start_polling)
        
        # Run polling with callback
        asyncio.run(self.manager.start_polling_with_retry(
            mock_dp,
            mock_bot,
            on_conflict_callback=conflict_callback
        ))
        
        # Callback should have been executed once (for the one conflict)
        self.assertEqual(len(callback_executed), 1)
    
    def test_async_conflict_callback(self):
        """Test that async conflict callback is supported."""
        mock_dp = Mock()
        mock_bot = Mock()
        callback_executed = []
        
        async def async_conflict_callback():
            callback_executed.append(True)
        
        call_count = 0
        
        async def mock_start_polling(bot):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise TelegramConflictError(method=Mock(), message="Conflict")
            return None
        
        mock_dp.start_polling = AsyncMock(side_effect=mock_start_polling)
        
        # Run polling with async callback
        asyncio.run(self.manager.start_polling_with_retry(
            mock_dp,
            mock_bot,
            on_conflict_callback=async_conflict_callback
        ))
        
        # Async callback should have been executed
        self.assertEqual(len(callback_executed), 1)
    
    def test_exponential_backoff_delay(self):
        """Test that delay increases exponentially."""
        # Create manager with specific values
        manager = PollingManager(
            max_retries=3,
            initial_delay=1.0,
            max_delay=10.0,
            backoff_factor=2.0
        )
        
        # Expected delays: 1.0, 2.0, 4.0, 8.0
        # After max_delay cap: 1.0, 2.0, 4.0, 8.0 (all within 10.0 max)
        
        mock_dp = Mock()
        mock_bot = Mock()
        
        delays = []
        
        async def mock_start_polling(bot):
            raise TelegramConflictError(method=Mock(), message="Conflict")
        
        mock_dp.start_polling = AsyncMock(side_effect=mock_start_polling)
        
        # Patch sleep to capture delays
        original_sleep = asyncio.sleep
        
        async def mock_sleep(delay):
            delays.append(delay)
            await original_sleep(0)  # Don't actually sleep
        
        with patch('asyncio.sleep', side_effect=mock_sleep):
            try:
                asyncio.run(manager.start_polling_with_retry(mock_dp, mock_bot))
            except TelegramConflictError:
                pass
        
        # Check that delays follow exponential pattern
        self.assertEqual(len(delays), 3)  # 3 retries
        self.assertAlmostEqual(delays[0], 1.0, places=1)
        self.assertAlmostEqual(delays[1], 2.0, places=1)
        self.assertAlmostEqual(delays[2], 4.0, places=1)
    
    def test_unexpected_error_propagates(self):
        """Test that unexpected errors are propagated."""
        mock_dp = Mock()
        mock_bot = Mock()
        
        async def mock_start_polling(bot):
            raise ValueError("Unexpected error")
        
        mock_dp.start_polling = AsyncMock(side_effect=mock_start_polling)
        
        # Should raise the unexpected error
        with self.assertRaises(ValueError):
            asyncio.run(self.manager.start_polling_with_retry(mock_dp, mock_bot))


if __name__ == '__main__':
    unittest.main()
