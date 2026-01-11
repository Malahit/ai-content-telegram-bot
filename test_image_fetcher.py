#!/usr/bin/env python3
"""
Unit tests for image_fetcher module using mocks.
Tests the Pexels API integration without requiring internet access.
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import logging
from image_fetcher import ImageFetcher

logging.basicConfig(level=logging.INFO)


class TestImageFetcher(unittest.TestCase):
    """Test cases for ImageFetcher class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.api_key = "test_api_key_12345"
        self.fetcher = ImageFetcher(api_key=self.api_key)
    
    def test_init_with_api_key(self):
        """Test ImageFetcher initialization with API key"""
        self.assertEqual(self.fetcher.api_key, self.api_key)
        self.assertEqual(self.fetcher.base_url, "https://api.pexels.com/v1")
        self.assertEqual(self.fetcher.session.headers.get("Authorization"), self.api_key)
    
    def test_init_without_api_key(self):
        """Test ImageFetcher initialization without API key"""
        fetcher = ImageFetcher(api_key=None)
        self.assertIsNone(fetcher.api_key)
    
    @patch('image_fetcher.requests.Session.get')
    def test_search_images_success(self, mock_get):
        """Test successful image search"""
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "photos": [
                {"src": {"large": "https://example.com/image1.jpg"}},
                {"src": {"large": "https://example.com/image2.jpg"}},
                {"src": {"large": "https://example.com/image3.jpg"}}
            ]
        }
        mock_get.return_value = mock_response
        
        # Test search
        results = self.fetcher.search_images("fitness", max_images=3)
        
        # Assertions
        self.assertEqual(len(results), 3)
        self.assertEqual(results[0], "https://example.com/image1.jpg")
        self.assertEqual(results[1], "https://example.com/image2.jpg")
        self.assertEqual(results[2], "https://example.com/image3.jpg")
        
        # Verify API was called correctly
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        self.assertIn("query", call_args.kwargs["params"])
        self.assertEqual(call_args.kwargs["params"]["query"], "fitness")
    
    @patch('image_fetcher.requests.Session.get')
    def test_search_images_no_api_key(self, mock_get):
        """Test image search without API key"""
        fetcher = ImageFetcher(api_key=None)
        results = fetcher.search_images("fitness")
        
        # Should return empty list without making API call
        self.assertEqual(results, [])
        mock_get.assert_not_called()
    
    @patch('image_fetcher.requests.Session.get')
    def test_search_images_http_error(self, mock_get):
        """Test image search with HTTP error"""
        # Mock HTTP error response
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_response.raise_for_status.side_effect = Exception("HTTP 401")
        mock_get.return_value = mock_response
        
        # Test search
        results = self.fetcher.search_images("fitness")
        
        # Should return empty list on error
        self.assertEqual(results, [])
    
    @patch('image_fetcher.requests.Session.get')
    def test_search_images_empty_results(self, mock_get):
        """Test image search with no results"""
        # Mock empty response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"photos": []}
        mock_get.return_value = mock_response
        
        # Test search
        results = self.fetcher.search_images("nonexistent_topic")
        
        # Should return empty list
        self.assertEqual(results, [])
    
    @patch('image_fetcher.requests.Session.get')
    def test_get_random_images_success(self, mock_get):
        """Test successful random image fetch"""
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "photos": [
                {"src": {"large": "https://example.com/random1.jpg"}},
                {"src": {"large": "https://example.com/random2.jpg"}}
            ]
        }
        mock_get.return_value = mock_response
        
        # Test fetch
        results = self.fetcher.get_random_images(count=2)
        
        # Assertions
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0], "https://example.com/random1.jpg")
        self.assertEqual(results[1], "https://example.com/random2.jpg")
    
    @patch('image_fetcher.requests.Session.get')
    def test_get_random_images_no_api_key(self, mock_get):
        """Test random image fetch without API key"""
        fetcher = ImageFetcher(api_key=None)
        results = fetcher.get_random_images()
        
        # Should return empty list without making API call
        self.assertEqual(results, [])
        mock_get.assert_not_called()


if __name__ == '__main__':
    # Run tests
    suite = unittest.TestLoader().loadTestsFromTestCase(TestImageFetcher)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Exit with appropriate code
    exit(0 if result.wasSuccessful() else 1)
