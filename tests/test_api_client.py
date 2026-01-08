"""
Unit tests for API client module.

Tests API client functionality, error handling, and retry logic.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import requests
from api_client import PerplexityAPIClient, PerplexityAPIError


class TestPerplexityAPIClient(unittest.TestCase):
    """Test cases for PerplexityAPIClient."""
    
    def setUp(self):
        """Set up test environment."""
        # Mock config to avoid loading real config
        self.config_patcher = patch('api_client.config')
        self.mock_config = self.config_patcher.start()
        self.mock_config.pplx_api_key = 'test_api_key'
        self.mock_config.api_timeout = 30
        self.mock_config.max_tokens = 800
        self.mock_config.temperature = 0.8
        self.mock_config.api_model = 'sonar'
        
        self.client = PerplexityAPIClient()
    
    def tearDown(self):
        """Clean up test environment."""
        self.config_patcher.stop()
    
    def test_build_headers(self):
        """Test that headers are built correctly."""
        headers = self.client._build_headers()
        
        self.assertIn('Authorization', headers)
        self.assertIn('Content-Type', headers)
        self.assertEqual(headers['Content-Type'], 'application/json')
    
    def test_build_request_data(self):
        """Test that request data is built correctly."""
        data = self.client._build_request_data('test topic')
        
        self.assertIn('model', data)
        self.assertIn('messages', data)
        self.assertIn('max_tokens', data)
        self.assertIn('temperature', data)
        self.assertEqual(data['model'], 'sonar')
        self.assertEqual(len(data['messages']), 2)
    
    def test_build_request_data_with_rag_context(self):
        """Test that RAG context is included in request data."""
        rag_context = "This is RAG context"
        data = self.client._build_request_data('test topic', rag_context)
        
        user_message = data['messages'][1]['content']
        self.assertIn(rag_context, user_message)
        self.assertIn('test topic', user_message)
    
    @patch('api_client.requests.post')
    def test_generate_content_success(self, mock_post):
        """Test successful content generation."""
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'choices': [
                {
                    'message': {
                        'content': 'Generated content here'
                    }
                }
            ]
        }
        mock_post.return_value = mock_response
        
        content = self.client.generate_content('test topic')
        
        self.assertEqual(content, 'Generated content here')
        mock_post.assert_called_once()
    
    @patch('api_client.requests.post')
    def test_generate_content_timeout_retry(self, mock_post):
        """Test that client retries on timeout."""
        # Mock timeout on first call, success on second
        mock_post.side_effect = [
            requests.exceptions.Timeout('Timeout'),
            Mock(
                status_code=200,
                json=lambda: {
                    'choices': [{'message': {'content': 'Success'}}]
                }
            )
        ]
        
        content = self.client.generate_content('test topic')
        
        self.assertEqual(content, 'Success')
        self.assertEqual(mock_post.call_count, 2)
    
    @patch('api_client.requests.post')
    def test_generate_content_max_retries(self, mock_post):
        """Test that client fails after max retries."""
        # Mock continuous failures
        mock_post.side_effect = requests.exceptions.Timeout('Timeout')
        
        with self.assertRaises(PerplexityAPIError):
            self.client.generate_content('test topic')
        
        # Should try 3 times (max_retries)
        self.assertEqual(mock_post.call_count, 3)
    
    @patch('api_client.requests.post')
    def test_generate_content_http_error_4xx_no_retry(self, mock_post):
        """Test that client doesn't retry on 4xx errors."""
        # Mock 400 error
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError('Bad Request')
        mock_post.return_value = mock_response
        
        with self.assertRaises(PerplexityAPIError):
            self.client.generate_content('test topic')
        
        # Should only try once for 4xx errors
        self.assertEqual(mock_post.call_count, 1)
    
    def test_extract_content_success(self):
        """Test successful content extraction."""
        response_data = {
            'choices': [
                {
                    'message': {
                        'content': '  Test content  '
                    }
                }
            ]
        }
        
        content = self.client._extract_content(response_data)
        self.assertEqual(content, 'Test content')
    
    def test_extract_content_empty_raises_error(self):
        """Test that empty content raises error."""
        response_data = {
            'choices': [
                {
                    'message': {
                        'content': '   '
                    }
                }
            ]
        }
        
        with self.assertRaises(PerplexityAPIError):
            self.client._extract_content(response_data)
    
    def test_extract_content_invalid_structure_raises_error(self):
        """Test that invalid response structure raises error."""
        response_data = {
            'invalid': 'structure'
        }
        
        with self.assertRaises(PerplexityAPIError):
            self.client._extract_content(response_data)


if __name__ == '__main__':
    unittest.main()
