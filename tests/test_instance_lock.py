"""
Tests for instance lock functionality.

Tests the PID file-based locking mechanism to prevent multiple bot instances.
"""

import os
import sys
import unittest
import tempfile
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.instance_lock import InstanceLock


class TestInstanceLock(unittest.TestCase):
    """Test cases for InstanceLock class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary lock file for testing
        self.temp_dir = tempfile.mkdtemp()
        self.lock_file = os.path.join(self.temp_dir, "test_bot.lock")
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Remove lock file if it exists
        if os.path.exists(self.lock_file):
            os.remove(self.lock_file)
        # Remove temp directory and all contents
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_acquire_lock_first_time(self):
        """Test acquiring lock when no other instance is running."""
        lock = InstanceLock(self.lock_file)
        result = lock.acquire()
        
        self.assertTrue(result)
        self.assertTrue(os.path.exists(self.lock_file))
        
        # Verify PID is written correctly
        with open(self.lock_file, 'r') as f:
            pid = int(f.read().strip())
        self.assertEqual(pid, os.getpid())
        
        # Clean up
        lock.release()
    
    def test_acquire_lock_when_already_locked(self):
        """Test acquiring lock when another instance holds it."""
        # First instance acquires lock
        lock1 = InstanceLock(self.lock_file)
        result1 = lock1.acquire()
        self.assertTrue(result1)
        
        # Second instance tries to acquire the same lock
        lock2 = InstanceLock(self.lock_file)
        result2 = lock2.acquire()
        
        # Should fail because first instance is running
        self.assertFalse(result2)
        
        # Clean up
        lock1.release()
    
    def test_acquire_lock_with_stale_pid(self):
        """Test acquiring lock when lock file has stale PID."""
        # Write a fake PID that doesn't exist
        fake_pid = 999999  # Assuming this PID doesn't exist
        with open(self.lock_file, 'w') as f:
            f.write(str(fake_pid))
        
        # Try to acquire lock
        lock = InstanceLock(self.lock_file)
        result = lock.acquire()
        
        # Should succeed and overwrite stale lock
        self.assertTrue(result)
        
        # Verify new PID is written
        with open(self.lock_file, 'r') as f:
            pid = int(f.read().strip())
        self.assertEqual(pid, os.getpid())
        
        # Clean up
        lock.release()
    
    def test_release_lock(self):
        """Test releasing lock removes the lock file."""
        lock = InstanceLock(self.lock_file)
        lock.acquire()
        
        # Verify lock file exists
        self.assertTrue(os.path.exists(self.lock_file))
        
        # Release lock
        lock.release()
        
        # Verify lock file is removed
        self.assertFalse(os.path.exists(self.lock_file))
    
    def test_is_process_running_current_process(self):
        """Test that current process is detected as running."""
        lock = InstanceLock(self.lock_file)
        result = lock.is_process_running(os.getpid())
        self.assertTrue(result)
    
    def test_is_process_running_invalid_pid(self):
        """Test that invalid PID is detected as not running."""
        lock = InstanceLock(self.lock_file)
        result = lock.is_process_running(999999)
        self.assertFalse(result)
    
    def test_acquire_creates_parent_directory(self):
        """Test that acquire creates parent directories if needed."""
        nested_lock = os.path.join(self.temp_dir, "nested", "dir", "test.lock")
        lock = InstanceLock(nested_lock)
        result = lock.acquire()
        
        self.assertTrue(result)
        self.assertTrue(os.path.exists(nested_lock))
        
        # Clean up
        lock.release()


if __name__ == '__main__':
    unittest.main()
