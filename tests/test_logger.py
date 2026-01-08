"""
Unit tests for logger configuration module.

Tests logging setup and security filters.
"""

import logging
import unittest
from logger_config import SensitiveDataFilter, setup_logging


class TestSensitiveDataFilter(unittest.TestCase):
    """Test cases for SensitiveDataFilter."""
    
    def setUp(self):
        """Set up test environment."""
        self.filter = SensitiveDataFilter()
    
    def test_redacts_token(self):
        """Test that tokens are redacted from log messages."""
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='',
            lineno=0,
            msg='Bot token: abc123xyz',
            args=(),
            exc_info=None
        )
        
        self.filter.filter(record)
        self.assertIn('***REDACTED***', record.msg)
        self.assertNotIn('abc123xyz', record.msg)
    
    def test_redacts_api_key(self):
        """Test that API keys are redacted from log messages."""
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='',
            lineno=0,
            msg='API_KEY=sk-1234567890abcdef',
            args=(),
            exc_info=None
        )
        
        self.filter.filter(record)
        self.assertIn('***REDACTED***', record.msg)
        self.assertNotIn('sk-1234567890abcdef', record.msg)
    
    def test_redacts_bearer_token(self):
        """Test that bearer tokens are redacted from log messages."""
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='',
            lineno=0,
            msg='Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9',
            args=(),
            exc_info=None
        )
        
        self.filter.filter(record)
        self.assertIn('***REDACTED***', record.msg)
        self.assertNotIn('eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9', record.msg)
    
    def test_does_not_redact_safe_content(self):
        """Test that normal content is not redacted."""
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='',
            lineno=0,
            msg='Processing user request for topic: SMM',
            args=(),
            exc_info=None
        )
        
        original_msg = record.msg
        self.filter.filter(record)
        self.assertEqual(record.msg, original_msg)


class TestSetupLogging(unittest.TestCase):
    """Test cases for setup_logging function."""
    
    def test_creates_logger(self):
        """Test that setup_logging creates a logger."""
        logger = setup_logging()
        self.assertIsNotNone(logger)
        self.assertEqual(logger.name, 'ai_content_bot')
    
    def test_sets_log_level(self):
        """Test that setup_logging sets the correct log level."""
        logger = setup_logging(level=logging.DEBUG)
        self.assertEqual(logger.level, logging.DEBUG)
    
    def test_adds_sensitive_data_filter(self):
        """Test that setup_logging adds sensitive data filter."""
        logger = setup_logging()
        
        # Check that handler has the filter
        has_filter = False
        for handler in logger.handlers:
            for filter_obj in handler.filters:
                if isinstance(filter_obj, SensitiveDataFilter):
                    has_filter = True
                    break
        
        self.assertTrue(has_filter, "SensitiveDataFilter should be added to handler")
    
    def test_no_duplicate_handlers(self):
        """Test that calling setup_logging multiple times doesn't add duplicate handlers."""
        logger1 = setup_logging()
        handler_count_1 = len(logger1.handlers)
        
        logger2 = setup_logging()
        handler_count_2 = len(logger2.handlers)
        
        self.assertEqual(handler_count_1, handler_count_2)


if __name__ == '__main__':
    unittest.main()
