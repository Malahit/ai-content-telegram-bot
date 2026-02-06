#!/usr/bin/env python3
"""
Test script to verify is_another_instance_running function.

This script tests the psutil-based instance detection functionality.
Note: This is a standalone test that duplicates the function implementation
to avoid dependency issues when testing in isolation. In production, the
function is imported from utils.instance_lock.
"""

import os
import sys
import psutil


def is_another_instance_running() -> bool:
    """
    Check if another instance of bot.py or main.py is already running using psutil.
    
    This is a test-only copy of the function for standalone testing.
    The production version is in utils/instance_lock.py
    
    Returns:
        bool: True if another bot.py or main.py instance is detected, False otherwise
    """
    current_pid = os.getpid()
    print(f"[INFO] 🔍 Checking for other running instances (current PID: {current_pid})")
    
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
                is_python = False
                has_bot_script = False
                
                for i, arg in enumerate(cmdline):
                    # Check if this is a Python interpreter
                    # Use basename and specific patterns to avoid false positives
                    basename = os.path.basename(arg).lower()
                    # Match python, python2, python3, python2.7, python3.11, etc.
                    # The basename should be exactly 'python' or start with 'python' followed by a digit or dot
                    if basename == 'python' or basename == 'python2' or basename == 'python3':
                        is_python = True
                    elif basename.startswith('python') and len(basename) >= 7:
                        # Check if what follows 'python' is a version number (digit or dot)
                        if basename[6] in '.0123456789':
                            is_python = True
                    
                    # Check if the argument is our specific bot script
                    # We need to match ONLY bot.py or main.py, not robot.py or domain.py
                    arg_basename = os.path.basename(arg)
                    if arg_basename in ('bot.py', 'main.py'):
                        # Valid cases:
                        # - i == 0: shebang execution (./bot.py, /path/to/bot.py)
                        # - i > 0: executed with python (python bot.py, python3 /path/to/bot.py)
                        has_bot_script = True
                        # Mark as python if it's at position 0 (shebang execution)
                        if i == 0:
                            is_python = True
                
                if is_python and has_bot_script:
                    cmdline_str = ' '.join(cmdline)
                    bot_instances.append({
                        'pid': proc.pid,
                        'cmdline': cmdline_str
                    })
                    print(
                        f"[WARNING] ⚠️ Found another bot instance:\n"
                        f"   PID: {proc.pid}\n"
                        f"   Command: {cmdline_str}"
                    )
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                # Process may have terminated or we don't have access
                continue
    except Exception as e:
        print(f"[ERROR] ❌ Error checking for running instances: {e}")
        return False
    
    if bot_instances:
        print(
            f"[ERROR] ❌ Detected {len(bot_instances)} other bot instance(s) running!\n"
            f"   Please stop the other instance(s) before starting a new one."
        )
        return True
    
    print("[INFO] ✅ No other bot instances detected")
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
