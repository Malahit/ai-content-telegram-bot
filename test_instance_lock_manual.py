#!/usr/bin/env python3
"""
Manual test script to verify instance lock functionality.

This script demonstrates that the instance lock prevents multiple instances from running.
Run this script in two separate terminals to test the locking mechanism.
"""

import time
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.instance_lock import InstanceLock
from logger_config import logger


def main():
    """Test instance lock by holding it for 30 seconds."""
    logger.info("Starting instance lock test...")
    
    # Create instance lock
    lock = InstanceLock()
    
    # Try to acquire lock
    if not lock.acquire():
        logger.error("Failed to acquire lock. Another instance is running.")
        logger.info("Try running this script in another terminal to test the lock.")
        return 1
    
    logger.info("✅ Lock acquired successfully!")
    logger.info("Now try running this script in another terminal.")
    logger.info("The second instance should fail to acquire the lock.")
    logger.info("")
    logger.info("Holding lock for 30 seconds...")
    
    try:
        for i in range(30, 0, -1):
            logger.info(f"⏳ {i} seconds remaining...")
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("\n⚠️ Interrupted by user")
    finally:
        lock.release()
        logger.info("✅ Lock released")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
