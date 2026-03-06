#!/usr/bin/env python3
"""
Verification script for refactored modules.

This script verifies that all refactored modules can be imported
and work correctly without requiring external dependencies.
"""

import sys
import os

# Set test environment variables
os.environ['BOT_TOKEN'] = 'test_token_12345'
os.environ['PPLX_API_KEY'] = 'test_api_key_67890'

def test_config():
    """Test config module."""
    print("Testing config module...")
    from config import Config
    
    config = Config()
    assert config.bot_token == 'test_token_12345'
    assert config.pplx_api_key == 'test_api_key_67890'
    assert config.has_bot_token()
    assert config.has_api_key()
    
    safe_info = config.get_safe_config_info()
    assert safe_info['bot_token_configured']
    assert safe_info['api_key_configured']
    assert 'test_token' not in str(safe_info)
    assert 'test_api_key' not in str(safe_info)
    
    print("✅ Config module OK")

def test_logger():
    """Test logger module."""
    print("Testing logger module...")
    from logger_config import SensitiveDataFilter, logger
    
    assert logger.name == 'ai_content_bot'
    
    # Test filter
    import logging
    filter_obj = SensitiveDataFilter()
    record = logging.LogRecord(
        name='test', level=logging.INFO, pathname='', lineno=0,
        msg='token: abc123', args=(), exc_info=None
    )
    filter_obj.filter(record)
    assert '***REDACTED***' in record.msg
    assert 'abc123' not in record.msg
    
    print("✅ Logger module OK")

def test_api_client():
    """Test API client module."""
    print("Testing API client module...")
    from api_client import PerplexityAPIClient
    
    client = PerplexityAPIClient()
    assert client.api_key == 'test_api_key_67890'
    assert client.timeout == 45
    
    headers = client._build_headers()
    assert 'Authorization' in headers
    assert 'Content-Type' in headers
    
    data = client._build_request_data('test topic')
    assert data['model'] == 'sonar'
    assert len(data['messages']) == 2
    
    print("✅ API client module OK")

def test_translation_service():
    """Test translation service module."""
    print("Testing translation service module...")
    from translation_service import TranslationService
    
    service = TranslationService()
    # Should be disabled without dependencies
    assert not service.is_enabled()
    
    print("✅ Translation service module OK")

def test_rag_service():
    """Test RAG service module."""
    print("Testing RAG service module...")
    from rag_service import RAGService
    
    service = RAGService()
    # May or may not be enabled depending on dependencies
    status = service.get_status_info()
    assert 'enabled' in status
    assert 'vectorstore_loaded' in status
    
    print("✅ RAG service module OK")

def main():
    """Run all tests."""
    print("=" * 60)
    print("Refactored Modules Verification")
    print("=" * 60)
    print()
    
    try:
        test_config()
        test_logger()
        test_api_client()
        test_translation_service()
        test_rag_service()
        
        print()
        print("=" * 60)
        print("✅ ALL VERIFICATION TESTS PASSED")
        print("=" * 60)
        print()
        print("The refactored code is working correctly!")
        print("All modules can be imported and initialized properly.")
        print()
        return 0
        
    except Exception as e:
        print()
        print("=" * 60)
        print("❌ VERIFICATION FAILED")
        print("=" * 60)
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
