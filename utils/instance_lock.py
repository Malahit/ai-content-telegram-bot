"""
Instance lock manager to prevent multiple bot instances from running simultaneously.

This module provides a file-based locking mechanism to ensure only one bot instance
runs at a time, preventing Telegram API conflicts from concurrent getUpdates requests.
"""

import os
import sys
import signal
import atexit
import tempfile
from pathlib import Path
from logger_config import logger
import psutil


def is_another_instance_running() -> bool:
    """
    Check if another instance of bot.py is already running using psutil.
    
    This function scans all running processes to detect if any other instance
    of bot.py is running (excluding the current process).
    
    Returns:
        bool: True if another bot.py instance is detected, False otherwise
    """
    current_pid = os.getpid()
    logger.info(f"🔍 Checking for other running instances (current PID: {current_pid})")
    
    bot_instances = []
    
    try:
        # Iterate through all running processes
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                # Skip the current process
                if proc.pid == current_pid:
                    continue
                
                # Get process command line
                cmdline = proc.info.get('cmdline')
                if not cmdline:
                    continue
                
                # Check if this is a Python process running bot.py or main.py
                # We look for:
                # 1. The process must be running with python interpreter
                # 2. The script name must be bot.py or main.py (as the actual script argument)
                is_python = False
                has_bot_script = False
                
                for i, arg in enumerate(cmdline):
                    # Check if this is a Python interpreter
                    if 'python' in arg.lower():
                        is_python = True
                    
                    # Check if the argument is our bot script (not just containing the name)
                    # Match patterns like: bot.py, ./bot.py, /path/to/bot.py
                    if arg.endswith('bot.py') or arg.endswith('main.py'):
                        # Verify it's an actual script argument, not just part of a path
                        if i > 0 or 'python' in cmdline[0].lower():
                            has_bot_script = True
                
                if is_python and has_bot_script:
                    cmdline_str = ' '.join(cmdline)
                    bot_instances.append({
                        'pid': proc.pid,
                        'cmdline': cmdline_str
                    })
                    logger.warning(
                        f"⚠️ Found another bot instance:\n"
                        f"   PID: {proc.pid}\n"
                        f"   Command: {cmdline_str}"
                    )
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                # Process may have terminated or we don't have access
                continue
    except Exception as e:
        logger.error(f"❌ Error checking for running instances: {e}")
        return False
    
    if bot_instances:
        logger.error(
            f"❌ Detected {len(bot_instances)} other bot instance(s) running!\n"
            f"   Please stop the other instance(s) before starting a new one."
        )
        return True
    
    logger.info("✅ No other bot instances detected")
    return False


class InstanceLock:
    """
    Manages instance locking using a PID file to prevent multiple bot instances.
    
    Note: Signal handlers are registered here for cleanup on termination.
    The ShutdownManager provides additional async cleanup for graceful shutdown.
    
    Attributes:
        lock_file: Path to the lock file
        pid: Current process ID
    """
    
    def __init__(self, lock_file: str = None):
        """
        Initialize the instance lock manager.
        
        Args:
            lock_file: Path to the lock file. If None, uses cross-platform temp directory
        """
        if lock_file is None:
            # Use cross-platform temp directory
            lock_file = os.path.join(tempfile.gettempdir(), "telegram_bot.lock")
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
            # Note: These signal handlers provide basic cleanup for the lock file.
            # For full async cleanup, the ShutdownManager should be used alongside this.
            atexit.register(self.release)
            
            # Only register signal handlers if not on Windows (which doesn't support signal.SIGTERM properly)
            if sys.platform != 'win32':
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
