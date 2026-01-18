"""
Logger configuration module for AI Content Telegram Bot.

Provides secure logging with sensitive data filtering.
"""

import logging
import re
import sys
from typing import Optional


class SensitiveDataFilter(logging.Filter):
    """
    Filter to redact sensitive data from log messages.
    """
    
    # Patterns for sensitive data
    PATTERNS = [
        (re.compile(r'(token["\s:=]+)[a-zA-Z0-9_-]+', re.IGNORECASE), r'\1***REDACTED***'),
        (re.compile(r'(api[_-]?key["\s:=]+)[a-zA-Z0-9_-]+', re.IGNORECASE), r'\1***REDACTED***'),
        (re.compile(r'(Bearer\s+)[a-zA-Z0-9._-]+', re.IGNORECASE), r'\1***REDACTED***'),
        (re.compile(r'(sk-[a-zA-Z0-9]{20,})'), r'***REDACTED***'),
    ]
    
    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        
        # Apply all redaction patterns
        for pattern, replacement in self.PATTERNS:
            message = pattern.sub(replacement, message)
        
        # Apply additional sensitive data masking
        message = self.mask_sensitive_data(message)
        
        record.msg = message
        record.args = ()
        return True
    
    def mask_sensitive_data(self, message: str) -> str:
        """Additional masking for sensitive data."""
        # Mask anything that looks like a key after "key=" or "key:"
        message = re.sub(r'(key[=:]\s*)[\w-]{10,}', r'\1***REDACTED***', message, flags=re.IGNORECASE)
        return message


class SuccessLogger(logging.Logger):
    """
    Extended logger with success level.
    """
    SUCCESS = 25  # Between INFO and WARNING
    
    def __init__(self, name: str, level=logging.NOTSET):
        super().__init__(name, level)
        logging.addLevelName(self.SUCCESS, "SUCCESS")
    
    def success(self, message, *args, **kwargs):
        """Log a success message."""
        if self.isEnabledFor(self.SUCCESS):
            self._log(self.SUCCESS, message, args, **kwargs)


def setup_logging(name: str = 'ai_content_bot', level: int = logging.INFO) -> SuccessLogger:
    """
    Setup logging with sensitive data filtering.
    
    Args:
        name: Logger name
        level: Logging level
        
    Returns:
        Configured logger instance
    """
    # Set custom logger class
    logging.setLoggerClass(SuccessLogger)
    
    # Get or create logger
    logger = logging.getLogger(name)
    
    # Set level (even if logger already exists)
    logger.setLevel(level)
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    
    # Add sensitive data filter
    handler.addFilter(SensitiveDataFilter())
    
    # Add handler to logger
    logger.addHandler(handler)
    
    return logger


# Global logger instance
logger = setup_logging()
