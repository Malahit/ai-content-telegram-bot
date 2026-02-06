"""
Integration test for bot startup and shutdown with instance lock.

This test verifies that the bot can start, acquire the instance lock,
and shut down cleanly with all resources released.
"""

import os
import sys
import unittest
import asyncio
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import InstanceLock, shutdown_manager, PollingManager


class TestBotIntegration(unittest.TestCase):
    """Integration tests for bot startup and shutdown."""
    
    def setUp(self):
        """Set up test fixtures."""
        import tempfile
        self.temp_dir = tempfile.mkdtemp()
        self.lock_file = os.path.join(self.temp_dir, "test_bot.lock")
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_bot_startup_shutdown_cycle(self):
        """Test complete bot startup and shutdown cycle."""
        
        async def run_bot_cycle():
            # Create a fresh shutdown manager for this test
            from utils.shutdown_manager import ShutdownManager
            test_shutdown_manager = ShutdownManager()
            
            # Simulate bot startup
            instance_lock = InstanceLock(self.lock_file)
            
            # Acquire lock
            acquired = instance_lock.acquire()
            self.assertTrue(acquired, "Failed to acquire instance lock")
            
            # Verify lock file exists
            self.assertTrue(Path(self.lock_file).exists())
            
            # Register shutdown callback
            shutdown_called = []
            
            async def on_shutdown():
                shutdown_called.append(True)
            
            test_shutdown_manager.register_callback(on_shutdown)
            
            # Simulate some work
            await asyncio.sleep(0.1)
            
            # Shutdown
            await test_shutdown_manager.shutdown()
            
            # Verify shutdown callback was called
            self.assertEqual(len(shutdown_called), 1)
            
            # Release lock
            instance_lock.release()
            
            # Verify lock file is removed
            self.assertFalse(Path(self.lock_file).exists())
        
        # Run the async test
        asyncio.run(run_bot_cycle())
    
    def test_second_instance_blocked(self):
        """Test that second instance is blocked when first holds lock."""
        
        async def run_test():
            # First instance
            lock1 = InstanceLock(self.lock_file)
            acquired1 = lock1.acquire()
            self.assertTrue(acquired1)
            
            try:
                # Second instance should fail
                lock2 = InstanceLock(self.lock_file)
                acquired2 = lock2.acquire()
                self.assertFalse(acquired2, "Second instance should not acquire lock")
            finally:
                lock1.release()
        
        asyncio.run(run_test())
    
    def test_polling_manager_integration(self):
        """Test polling manager with mocked dispatcher."""
        
        async def run_test():
            # Create mocks
            mock_dp = Mock()
            mock_bot = Mock()
            
            # Track polling calls
            call_count = 0
            
            async def mock_start_polling(bot):
                nonlocal call_count
                call_count += 1
                return None
            
            mock_dp.start_polling = AsyncMock(side_effect=mock_start_polling)
            
            # Create polling manager
            polling_manager = PollingManager(max_retries=3, initial_delay=0.1)
            
            # Start polling
            await polling_manager.start_polling_with_retry(mock_dp, mock_bot)
            
            # Verify polling was called
            self.assertEqual(call_count, 1)
        
        asyncio.run(run_test())
    
    def test_full_startup_flow(self):
        """Test complete startup flow with all components."""
        
        async def run_test():
            # Create a fresh shutdown manager for this test
            from utils.shutdown_manager import ShutdownManager
            test_shutdown_manager = ShutdownManager()
            
            # 1. Acquire instance lock
            instance_lock = InstanceLock(self.lock_file)
            self.assertTrue(instance_lock.acquire())
            
            try:
                # 2. Setup scheduler mock
                scheduler_stopped = []
                
                class MockScheduler:
                    running = True
                    
                    def shutdown(self, wait=True):
                        scheduler_stopped.append(True)
                        self.running = False
                
                scheduler = MockScheduler()
                
                # 3. Register shutdown callback
                async def on_shutdown():
                    if scheduler.running:
                        scheduler.shutdown(wait=False)
                
                test_shutdown_manager.register_callback(on_shutdown)
                
                # 4. Simulate some work
                await asyncio.sleep(0.1)
                
                # 5. Shutdown
                await test_shutdown_manager.shutdown()
                
                # 6. Verify cleanup
                self.assertEqual(len(scheduler_stopped), 1)
                
            finally:
                # 7. Release lock
                instance_lock.release()
                self.assertFalse(Path(self.lock_file).exists())
        
        asyncio.run(run_test())


if __name__ == '__main__':
    unittest.main()
