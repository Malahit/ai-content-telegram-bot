"""
Tests for shutdown manager functionality.

Tests the graceful shutdown mechanism and callback registration.
"""

import os
import sys
import unittest
import asyncio

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.shutdown_manager import ShutdownManager


class TestShutdownManager(unittest.TestCase):
    """Test cases for ShutdownManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.manager = ShutdownManager()
        self.callback_executed = []
    
    def tearDown(self):
        """Clean up test fixtures."""
        self.callback_executed.clear()
    
    def test_register_callback(self):
        """Test registering a shutdown callback."""
        async def test_callback():
            self.callback_executed.append('test')
        
        self.manager.register_callback(test_callback)
        self.assertIn(test_callback, self.manager.shutdown_callbacks)
    
    def test_register_duplicate_callback(self):
        """Test that duplicate callbacks are not registered twice."""
        async def test_callback():
            self.callback_executed.append('test')
        
        self.manager.register_callback(test_callback)
        self.manager.register_callback(test_callback)
        
        # Should only be registered once
        count = self.manager.shutdown_callbacks.count(test_callback)
        self.assertEqual(count, 1)
    
    def test_shutdown_executes_callbacks(self):
        """Test that shutdown executes all registered callbacks."""
        async def callback1():
            self.callback_executed.append('callback1')
        
        async def callback2():
            self.callback_executed.append('callback2')
        
        self.manager.register_callback(callback1)
        self.manager.register_callback(callback2)
        
        # Run shutdown
        asyncio.run(self.manager.shutdown())
        
        # Both callbacks should have been executed
        self.assertIn('callback1', self.callback_executed)
        self.assertIn('callback2', self.callback_executed)
    
    def test_shutdown_executes_callbacks_in_reverse_order(self):
        """Test that callbacks are executed in LIFO order."""
        async def callback1():
            self.callback_executed.append('first')
        
        async def callback2():
            self.callback_executed.append('second')
        
        self.manager.register_callback(callback1)
        self.manager.register_callback(callback2)
        
        # Run shutdown
        asyncio.run(self.manager.shutdown())
        
        # Callbacks should be executed in reverse order
        self.assertEqual(self.callback_executed, ['second', 'first'])
    
    def test_shutdown_handles_callback_errors(self):
        """Test that errors in callbacks don't stop shutdown process."""
        async def good_callback():
            self.callback_executed.append('good')
        
        async def bad_callback():
            raise Exception("Test error")
        
        async def another_good_callback():
            self.callback_executed.append('another_good')
        
        self.manager.register_callback(good_callback)
        self.manager.register_callback(bad_callback)
        self.manager.register_callback(another_good_callback)
        
        # Run shutdown - should not raise exception
        asyncio.run(self.manager.shutdown())
        
        # Good callbacks should still execute
        self.assertIn('good', self.callback_executed)
        self.assertIn('another_good', self.callback_executed)
    
    def test_shutdown_sets_event(self):
        """Test that shutdown sets the shutdown event."""
        self.assertFalse(self.manager.shutdown_event.is_set())
        
        asyncio.run(self.manager.shutdown())
        
        self.assertTrue(self.manager.shutdown_event.is_set())
    
    def test_shutdown_prevents_duplicate_execution(self):
        """Test that shutdown can only run once."""
        async def callback():
            self.callback_executed.append('callback')
        
        self.manager.register_callback(callback)
        
        # Run shutdown twice
        asyncio.run(self.manager.shutdown())
        asyncio.run(self.manager.shutdown())
        
        # Callback should only execute once
        self.assertEqual(len(self.callback_executed), 1)
    
    def test_supports_sync_callbacks(self):
        """Test that synchronous callbacks are supported."""
        def sync_callback():
            self.callback_executed.append('sync')
        
        self.manager.register_callback(sync_callback)
        asyncio.run(self.manager.shutdown())
        
        self.assertIn('sync', self.callback_executed)


if __name__ == '__main__':
    unittest.main()
