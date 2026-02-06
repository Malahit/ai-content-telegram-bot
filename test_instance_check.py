#!/usr/bin/env python3
"""
Test script to verify is_another_instance_running function.

This script tests the psutil-based instance detection functionality.
"""

import os
import sys
import time

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import directly to avoid dependency issues
import psutil
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'utils'))

# Mock the logger to avoid dependencies
class MockLogger:
    def info(self, msg):
        print(f"[INFO] {msg}")
    def warning(self, msg):
        print(f"[WARNING] {msg}")
    def error(self, msg):
        print(f"[ERROR] {msg}")

# Create a simple test
def is_another_instance_running() -> bool:
    """
    Check if another instance of bot.py is already running using psutil.
    
    This function scans all running processes to detect if any other instance
    of bot.py is running (excluding the current process).
    
    Returns:
        bool: True if another bot.py instance is detected, False otherwise
    """
    current_pid = os.getpid()
    logger = MockLogger()
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
                if cmdline:
                    # Check if bot.py or main.py is in the command line
                    cmdline_str = ' '.join(cmdline)
                    if 'bot.py' in cmdline_str or 'main.py' in cmdline_str:
                        # Ensure it's actually running Python with our bot files
                        if any('python' in arg.lower() for arg in cmdline):
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


def main():
    """Test the is_another_instance_running function."""
    print("=" * 60)
    print("Testing is_another_instance_running function")
    print("=" * 60)
    
    # Test 1: Check for running instances
    print("\n📋 Test 1: Checking for other running instances")
    result = is_another_instance_running()
    
    if result:
        print("✅ Test passed: Function detected other instances")
    else:
        print("✅ Test passed: No other instances detected")
    
    print("\n" + "=" * 60)
    print("Test completed successfully!")
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
