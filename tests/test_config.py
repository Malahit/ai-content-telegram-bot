"""
Unit tests for configuration module.

Tests configuration loading, validation, and security features.
"""

import os
import unittest
from unittest.mock import patch
from config import Config


class TestConfig(unittest.TestCase):
    """Test cases for Config class."""
    
    def setUp(self):
        """Set up test environment."""
        # Store original env vars
        self.original_env = os.environ.copy()
    
    def tearDown(self):
        """Clean up test environment."""
        # Restore original env vars
        os.environ.clear()
        os.environ.update(self.original_env)
    
    @patch.dict(os.environ, {
        'BOT_TOKEN': 'test_token_123',
        'PPLX_API_KEY': 'test_api_key_456'
    })
    def test_config_loads_required_vars(self):
        """Test that required environment variables are loaded."""
        config = Config()
        self.assertEqual(config.bot_token, 'test_token_123')
        self.assertEqual(config.pplx_api_key, 'test_api_key_456')
    
    @patch.dict(os.environ, {
        'BOT_TOKEN': 'test_token_123',
        'PPLX_API_KEY': 'test_api_key_456',
        'CHANNEL_ID': '@my_channel'
    })
    def test_config_loads_optional_vars(self):
        """Test that optional environment variables are loaded."""
        config = Config()
        self.assertEqual(config.channel_id, '@my_channel')
    
    @patch.dict(os.environ, {
        'BOT_TOKEN': 'test_token_123',
        'PPLX_API_KEY': 'test_api_key_456',
        'API_TIMEOUT': '60',
        'MAX_TOKENS': '1000',
        'TEMPERATURE': '0.9'
    })
    def test_config_loads_with_custom_values(self):
        """Test that custom configuration values are loaded."""
        config = Config()
        self.assertEqual(config.api_timeout, 60)
        self.assertEqual(config.max_tokens, 1000)
        self.assertEqual(config.temperature, 0.9)
    
    @patch.dict(os.environ, {}, clear=True)
    def test_config_raises_error_without_bot_token(self):
        """Test that Config raises error when BOT_TOKEN is missing."""
        with self.assertRaises(RuntimeError) as context:
            Config()
        self.assertIn('BOT_TOKEN', str(context.exception))
    
    @patch.dict(os.environ, {'BOT_TOKEN': 'test_token_123'}, clear=True)
    def test_config_raises_error_without_api_key(self):
        """Test that Config raises error when PPLX_API_KEY is missing."""
        with self.assertRaises(RuntimeError) as context:
            Config()
        self.assertIn('PPLX_API_KEY', str(context.exception))
    
    @patch.dict(os.environ, {
        'BOT_TOKEN': 'test_token_123',
        'PPLX_API_KEY': 'test_api_key_456'
    })
    def test_has_bot_token(self):
        """Test has_bot_token method."""
        config = Config()
        self.assertTrue(config.has_bot_token())
    
    @patch.dict(os.environ, {
        'BOT_TOKEN': 'test_token_123',
        'PPLX_API_KEY': 'test_api_key_456'
    })
    def test_has_api_key(self):
        """Test has_api_key method."""
        config = Config()
        self.assertTrue(config.has_api_key())
    
    @patch.dict(os.environ, {
        'BOT_TOKEN': 'test_token_123',
        'PPLX_API_KEY': 'test_api_key_456'
    })
    def test_get_safe_config_info_no_sensitive_data(self):
        """Test that safe config info doesn't expose sensitive data."""
        config = Config()
        safe_info = config.get_safe_config_info()
        
        # Should have status flags
        self.assertIn('bot_token_configured', safe_info)
        self.assertIn('api_key_configured', safe_info)
        
        # Should not have actual tokens
        self.assertNotIn('test_token_123', str(safe_info))
        self.assertNotIn('test_api_key_456', str(safe_info))
        
        # Should have non-sensitive config
        self.assertIn('channel_id', safe_info)
        self.assertIn('api_model', safe_info)


if __name__ == '__main__':
    unittest.main()
