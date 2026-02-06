"""
Polling manager with retry logic and exponential backoff.

Handles Telegram API conflicts and implements retry strategies to recover
from temporary issues with multiple bot instances.
"""

import asyncio
from typing import Optional
from aiogram import Bot, Dispatcher
from aiogram.exceptions import TelegramConflictError
from logger_config import logger


class PollingManager:
    """
    Manages bot polling with retry logic and conflict handling.
    
    Attributes:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds before first retry
        max_delay: Maximum delay in seconds between retries
        backoff_factor: Multiplier for exponential backoff
    """
    
    def __init__(
        self,
        max_retries: int = 5,
        initial_delay: float = 5.0,
        max_delay: float = 300.0,
        backoff_factor: float = 2.0
    ):
        """
        Initialize the polling manager.
        
        Args:
            max_retries: Maximum retry attempts (default: 5)
            initial_delay: Initial delay before retry in seconds (default: 5.0)
            max_delay: Maximum delay between retries in seconds (default: 300.0)
            backoff_factor: Exponential backoff multiplier (default: 2.0)
        """
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
    
    async def start_polling_with_retry(
        self,
        dispatcher: Dispatcher,
        bot: Bot,
        on_conflict_callback: Optional[callable] = None
    ):
        """
        Start polling with automatic retry on conflicts.
        
        Args:
            dispatcher: Aiogram Dispatcher instance
            bot: Aiogram Bot instance
            on_conflict_callback: Optional callback to execute on conflict detection
            
        Raises:
            TelegramConflictError: If max retries exceeded
        """
        retry_count = 0
        delay = self.initial_delay
        
        while retry_count <= self.max_retries:
            try:
                logger.info(
                    f"🚀 Starting bot polling (attempt {retry_count + 1}/{self.max_retries + 1})..."
                )
                
                # Start polling - this will block until error or shutdown
                await dispatcher.start_polling(bot)
                
                # If we reach here, polling stopped normally
                logger.info("✅ Polling stopped normally")
                break
                
            except TelegramConflictError as e:
                retry_count += 1
                
                logger.error(
                    f"❌ TelegramConflictError: {e}\n"
                    f"Another bot instance may be running.\n"
                    f"Retry attempt {retry_count}/{self.max_retries}"
                )
                
                # Execute conflict callback if provided
                if on_conflict_callback:
                    try:
                        if asyncio.iscoroutinefunction(on_conflict_callback):
                            await on_conflict_callback()
                        else:
                            on_conflict_callback()
                    except Exception as cb_error:
                        logger.error(f"Error in conflict callback: {cb_error}")
                
                # Check if we should retry
                if retry_count > self.max_retries:
                    logger.error(
                        f"❌ Max retries ({self.max_retries}) exceeded.\n"
                        f"Please ensure no other bot instances are running.\n"
                        f"Check for processes and lock files."
                    )
                    raise
                
                # Calculate delay with exponential backoff
                current_delay = min(delay, self.max_delay)
                logger.warning(
                    f"⏳ Waiting {current_delay:.1f} seconds before retry...\n"
                    f"💡 Tip: Check for other running instances or stale lock files."
                )
                
                await asyncio.sleep(current_delay)
                delay *= self.backoff_factor
                
            except Exception as e:
                # Handle other unexpected errors
                logger.error(
                    f"❌ Unexpected error during polling: {type(e).__name__}: {e}",
                    exc_info=True
                )
                raise
