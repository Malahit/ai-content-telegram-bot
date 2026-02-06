"""
Graceful shutdown manager for the Telegram bot.

Handles cleanup of resources including schedulers, API clients, and database connections
when the bot shuts down normally or receives termination signals.
"""

import asyncio
import signal
import sys
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
        self._loop = None  # Store event loop reference for signal handling
    
    def register_callback(self, callback: Callable):
        """
        Register a callback to be executed on shutdown.
        
        Args:
            callback: Async function to call during shutdown
        """
        if callback not in self.shutdown_callbacks:
            self.shutdown_callbacks.append(callback)
            logger.debug(f"Registered shutdown callback: {callback.__name__}")
    
    def shutdown_gracefully(self, signum, frame):
        """
        Handle SIGTERM signal for graceful shutdown.
        
        This function is called when SIGTERM is received. It initiates
        the shutdown process and terminates the script cleanly.
        
        **Important**: This function blocks briefly (up to 2 seconds) to allow
        shutdown callbacks (including scheduler shutdown) to complete before
        calling sys.exit(). This is necessary to ensure resources are properly
        freed, as required by the problem specification.
        
        **Limitations**: 
        - Blocking in signal handlers can be problematic if the signal interrupts 
          certain system calls
        - This approach assumes the signal is received from outside the process
        - In rare cases, sys.exit() from a signal handler may cause interpreter 
          state issues
        
        **Rationale**: The design prioritizes resource cleanup over pure signal 
        handler best practices, as the alternative (non-blocking with flags) 
        would not guarantee scheduler shutdown before process termination.
        
        Args:
            signum: Signal number
            frame: Current stack frame
        """
        # Get signal name safely (Python 3.5+)
        try:
            signal_name = signal.Signals(signum).name
        except (AttributeError, ValueError):
            signal_name = f"signal {signum}"
        
        logger.info(f"⚠️ Received {signal_name}, initiating graceful shutdown...")
        
        # Schedule shutdown in the event loop if available
        if self._loop and self._loop.is_running():
            # Schedule the shutdown coroutine and wait for it to complete
            # We use a short timeout to avoid hanging indefinitely
            try:
                future = asyncio.run_coroutine_threadsafe(self.shutdown(), self._loop)
                # Wait for shutdown to complete with a 2-second timeout
                future.result(timeout=2.0)
                logger.info("✅ Shutdown completed successfully")
            except TimeoutError:
                logger.warning("⚠️ Shutdown timed out after 2 seconds")
            except Exception as e:
                logger.error(f"❌ Error during shutdown: {e}")
        else:
            # If no loop is available, perform immediate exit
            logger.info("🛑 No event loop available")
        
        # Exit cleanly - atexit handlers will run
        logger.info("✅ Exiting process")
        sys.exit(0)
    
    def register_signals(self):
        """
        Register signal handlers for graceful shutdown using signal.signal.
        
        Handles SIGTERM and SIGINT signals using the signal library
        for cross-platform compatibility.
        """
        if self._signals_registered:
            return
        
        try:
            # Store the event loop reference for use in signal handlers
            try:
                self._loop = asyncio.get_event_loop()
            except RuntimeError:
                # No event loop in current thread
                self._loop = None
            
            # Use signal.signal for SIGTERM (cross-platform)
            signal.signal(signal.SIGTERM, self.shutdown_gracefully)
            # Also handle SIGINT (Ctrl+C) for consistency
            signal.signal(signal.SIGINT, self.shutdown_gracefully)
            
            self._signals_registered = True
            logger.info("✅ Signal handlers registered for graceful shutdown (SIGTERM, SIGINT)")
        except (ValueError, OSError) as e:
            # Some systems may not support certain signals
            logger.warning(f"⚠️ Could not register signal handlers: {e}")
    
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
