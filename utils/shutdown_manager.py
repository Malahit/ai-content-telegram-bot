"""
Graceful shutdown manager for the Telegram bot.

Handles cleanup of resources including schedulers, API clients, and database connections
when the bot shuts down normally or receives termination signals.
"""

import asyncio
import signal
from typing import Optional, Callable, List
from logger_config import logger


class ShutdownManager:
    """
    Manages graceful shutdown of bot resources.
    
    Attributes:
        shutdown_callbacks: List of async callbacks to execute on shutdown
        shutdown_event: Event to signal shutdown in progress
    """
    
    def __init__(self):
        """Initialize the shutdown manager."""
        self.shutdown_callbacks: List[Callable] = []
        self.shutdown_event = asyncio.Event()
        self._signals_registered = False
    
    def register_callback(self, callback: Callable):
        """
        Register a callback to be executed on shutdown.
        
        Args:
            callback: Async function to call during shutdown
        """
        if callback not in self.shutdown_callbacks:
            self.shutdown_callbacks.append(callback)
            logger.debug(f"Registered shutdown callback: {callback.__name__}")
    
    def register_signals(self):
        """
        Register signal handlers for graceful shutdown.
        
        Handles SIGTERM and SIGINT signals.
        """
        if self._signals_registered:
            return
        
        try:
            loop = asyncio.get_event_loop()
            
            for sig in (signal.SIGTERM, signal.SIGINT):
                loop.add_signal_handler(
                    sig,
                    lambda s=sig: asyncio.create_task(self._signal_handler(s))
                )
            
            self._signals_registered = True
            logger.info("✅ Signal handlers registered for graceful shutdown")
        except NotImplementedError:
            # Windows doesn't support add_signal_handler
            logger.warning("⚠️ Signal handlers not available on this platform")
    
    async def _signal_handler(self, sig):
        """
        Handle termination signals.
        
        Args:
            sig: Signal number
        """
        signal_name = signal.Signals(sig).name
        logger.info(f"⚠️ Received {signal_name}, initiating graceful shutdown...")
        await self.shutdown()
    
    async def shutdown(self):
        """
        Execute all registered shutdown callbacks.
        
        Calls all registered cleanup functions in reverse order of registration.
        """
        if self.shutdown_event.is_set():
            logger.warning("⚠️ Shutdown already in progress")
            return
        
        self.shutdown_event.set()
        logger.info("🛑 Starting graceful shutdown...")
        
        # Execute callbacks in reverse order (LIFO)
        for callback in reversed(self.shutdown_callbacks):
            try:
                logger.info(f"🔄 Executing shutdown callback: {callback.__name__}")
                if asyncio.iscoroutinefunction(callback):
                    await callback()
                else:
                    callback()
            except Exception as e:
                logger.error(f"❌ Error in shutdown callback {callback.__name__}: {e}", exc_info=True)
        
        logger.info("✅ Graceful shutdown complete")


# Global shutdown manager instance
shutdown_manager = ShutdownManager()
