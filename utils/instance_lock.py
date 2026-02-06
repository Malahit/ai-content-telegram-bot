"""
Instance lock manager to prevent multiple bot instances from running simultaneously.

This module provides a file-based locking mechanism to ensure only one bot instance
runs at a time, preventing Telegram API conflicts from concurrent getUpdates requests.
"""

import os
import sys
import signal
import atexit
from pathlib import Path
from logger_config import logger


class InstanceLock:
    """
    Manages instance locking using a PID file to prevent multiple bot instances.
    
    Attributes:
        lock_file: Path to the lock file
        pid: Current process ID
    """
    
    def __init__(self, lock_file: str = "/tmp/telegram_bot.lock"):
        """
        Initialize the instance lock manager.
        
        Args:
            lock_file: Path to the lock file (default: /tmp/telegram_bot.lock)
        """
        self.lock_file = Path(lock_file)
        self.pid = os.getpid()
    
    def is_process_running(self, pid: int) -> bool:
        """
        Check if a process with given PID is running.
        
        Args:
            pid: Process ID to check
            
        Returns:
            bool: True if process is running, False otherwise
        """
        try:
            # Sending signal 0 doesn't kill the process, just checks if it exists
            os.kill(pid, 0)
            return True
        except (OSError, ProcessLookupError):
            return False
    
    def acquire(self) -> bool:
        """
        Acquire the instance lock.
        
        Returns:
            bool: True if lock acquired successfully, False if another instance is running
            
        Raises:
            SystemExit: If another instance is running with valid PID
        """
        # Check if lock file exists
        if self.lock_file.exists():
            try:
                # Read the PID from lock file
                with open(self.lock_file, 'r') as f:
                    old_pid = int(f.read().strip())
                
                # Check if the process is still running
                if self.is_process_running(old_pid):
                    logger.error(
                        f"⚠️ Another bot instance is already running (PID: {old_pid})\n"
                        f"Lock file: {self.lock_file}\n"
                        f"To force start, stop the other instance or remove the lock file."
                    )
                    return False
                else:
                    # Process is dead, remove stale lock file
                    logger.warning(
                        f"🔧 Removing stale lock file (PID {old_pid} not running)"
                    )
                    self.lock_file.unlink()
            except (ValueError, IOError) as e:
                logger.warning(f"⚠️ Invalid lock file, removing: {e}")
                try:
                    self.lock_file.unlink()
                except OSError:
                    pass
        
        # Create lock file with current PID
        try:
            self.lock_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.lock_file, 'w') as f:
                f.write(str(self.pid))
            
            logger.info(f"✅ Instance lock acquired (PID: {self.pid}, Lock: {self.lock_file})")
            
            # Register cleanup handlers
            atexit.register(self.release)
            signal.signal(signal.SIGTERM, self._signal_handler)
            signal.signal(signal.SIGINT, self._signal_handler)
            
            return True
        except IOError as e:
            logger.error(f"❌ Failed to create lock file: {e}")
            return False
    
    def release(self):
        """
        Release the instance lock by removing the lock file.
        """
        try:
            if self.lock_file.exists():
                # Verify it's our lock file before removing
                with open(self.lock_file, 'r') as f:
                    lock_pid = int(f.read().strip())
                
                if lock_pid == self.pid:
                    self.lock_file.unlink()
                    logger.info(f"🔓 Instance lock released (PID: {self.pid})")
                else:
                    logger.warning(
                        f"⚠️ Lock file belongs to another process (PID: {lock_pid}), not removing"
                    )
        except (IOError, ValueError, OSError) as e:
            logger.warning(f"⚠️ Error releasing lock: {e}")
    
    def _signal_handler(self, signum, frame):
        """
        Handle termination signals to ensure clean shutdown.
        
        Args:
            signum: Signal number
            frame: Current stack frame
        """
        signal_name = signal.Signals(signum).name
        logger.info(f"⚠️ Received {signal_name}, shutting down gracefully...")
        self.release()
        sys.exit(0)
