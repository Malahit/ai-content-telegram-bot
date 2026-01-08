"""
Logging configuration module for AI Content Telegram Bot.

This module sets up structured logging with appropriate levels and
security filters to prevent sensitive data from being logged.
"""

import logging
import re
from typing import Optional


class SensitiveDataFilter(logging.Filter):
    """
    Filter to redact sensitive information from logs.
    
    Prevents accidental logging of API keys, tokens, and other sensitive data.
    """
    
    # Patterns to detect and redact sensitive data
    PATTERNS = [
        (re.compile(r'(token["\s:=]+)([A-Za-z0-9_\-\.]+)', re.IGNORECASE), r'\1***REDACTED***'),
        (re.compile(r'(api[_\s]?key["\s:=]+)([A-Za-z0-9_\-\.]+)', re.IGNORECASE), r'\1***REDACTED***'),
        (re.compile(r'(bearer\s+)([A-Za-z0-9_\-\.]+)', re.IGNORECASE), r'\1***REDACTED***'),
        (re.compile(r'(password["\s:=]+)([^\s"]+)', re.IGNORECASE), r'\1***REDACTED***'),
    ]
    
    def filter(self, record: logging.LogRecord) -> bool:
        """
        Filter log record to redact sensitive information.
        
        Args:
            record: Log record to filter
            
        Returns:
            bool: Always True (we modify but don't block records)
        """
        message = record.getMessage()
        for pattern, replacement in self.PATTERNS:
            message = pattern.sub(replacement, message)
        
        # Update the record's message
        record.msg = message
        record.args = ()
        
        return True


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """
    Set up application logging with security filters.
    
    Args:
        level: Logging level (default: logging.INFO)
        
    Returns:
        logging.Logger: Configured logger instance
    """
    # Create logger
    logger = logging.getLogger("ai_content_bot")
    logger.setLevel(level)
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    # Create console handler with formatting
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    
    # Add sensitive data filter
    console_handler.addFilter(SensitiveDataFilter())
    
    # Add handler to logger
    logger.addHandler(console_handler)
    
    return logger


# Global logger instance
logger = setup_logging()
