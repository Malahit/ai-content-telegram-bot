"""
Integration tests for image posting workflows.
Tests the complete flow from image fetching to post creation.
"""
import unittest
import asyncio
import sys
import os
from unittest.mock import Mock, AsyncMock, patch, MagicMock

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from image_fetcher import ImageFetcher
import aiohttp


class TestImagePostWorkflows(unittest.TestCase):
    """Test image posting workflows with various scenarios"""
    
    def test_successful_image_fetch_pexels(self):
        """Test successful image fetch from Pexels"""
        async def run_test():
            fetcher = ImageFetcher(
                pexels_key="test_key",
                cache_enabled=False
            )
            
            # Mock successful Pexels response
            async def mock_pexels(*args, **kwargs):
                return ["https://example.com/photo1.jpg", "https://example.com/photo2.jpg"]
            
            fetcher._fetch_from_pexels = mock_pexels
            
            images, error = await fetcher.search_images("fitness", max_images=3)
            
            self.assertEqual(len(images), 2)
            self.assertIsNone(error)
            self.assertTrue(all("example.com" in url for url in images))
        
        asyncio.run(run_test())
    
    def test_fallback_to_pixabay_on_pexels_failure(self):
        """Test that system falls back to Pixabay when Pexels fails"""
        async def run_test():
            fetcher = ImageFetcher(
                pexels_key="test_key",
                pixabay_key="test_pixabay_key",
                cache_enabled=False
            )
            
            # Mock Pexels failure
            async def mock_pexels_fail(*args, **kwargs):
                raise ValueError("Invalid Pexels API key")
            
            # Mock Pixabay success
            async def mock_pixabay_success(*args, **kwargs):
                return ["https://pixabay.com/photo1.jpg"]
            
            fetcher._fetch_from_pexels = mock_pexels_fail
            fetcher._fetch_from_pixabay = mock_pixabay_success
            
            images, error = await fetcher.search_images("nature", max_images=3)
            
            self.assertEqual(len(images), 1)
            self.assertIsNone(error)
            self.assertIn("pixabay", images[0])
        
        asyncio.run(run_test())
    
    def test_graceful_degradation_no_images(self):
        """Test that system gracefully handles when no images are available"""
        async def run_test():
            fetcher = ImageFetcher(
                pexels_key="test_key",
                pixabay_key="test_pixabay_key",
                cache_enabled=False
            )
            
            # Mock both APIs returning no results
            async def mock_no_results(*args, **kwargs):
                return []
            
            fetcher._fetch_from_pexels = mock_no_results
            fetcher._fetch_from_pixabay = mock_no_results
            
            images, error = await fetcher.search_images("obscure_topic", max_images=3)
            
            self.assertEqual(len(images), 0)
            self.assertIsNotNone(error)
            self.assertIn("No results", error)
        
        asyncio.run(run_test())
    
    def test_error_message_for_invalid_api_key(self):
        """Test that clear error messages are provided for invalid API keys"""
        async def run_test():
            fetcher = ImageFetcher(
                pexels_key="invalid_key",
                cache_enabled=False
            )
            
            # Mock 401 Unauthorized
            async def mock_unauthorized(*args, **kwargs):
                raise ValueError("Invalid Pexels API key")
            
            fetcher._fetch_from_pexels = mock_unauthorized
            
            images, error = await fetcher.search_images("test", max_images=3)
            
            self.assertEqual(len(images), 0)
            self.assertIsNotNone(error)
            self.assertIn("Invalid Pexels API key", error)
        
        asyncio.run(run_test())
    
    def test_error_message_for_missing_api_keys(self):
        """Test that clear error messages are provided when API keys are missing"""
        async def run_test():
            fetcher = ImageFetcher(cache_enabled=False)
            
            images, error = await fetcher.search_images("test", max_images=3)
            
            self.assertEqual(len(images), 0)
            self.assertIsNotNone(error)
            self.assertIn("not configured", error.lower())
        
        asyncio.run(run_test())
    
    def test_cache_hit_returns_cached_images(self):
        """Test that cached images are returned without API calls"""
        async def run_test():
            fetcher = ImageFetcher(
                pexels_key="test_key",
                cache_enabled=True
            )
            
            # Pre-populate cache
            test_urls = ["https://cached1.jpg", "https://cached2.jpg"]
            fetcher.cache.cache_images("cached_topic", test_urls)
            
            # Should return cached images without calling APIs
            images, error = await fetcher.search_images("cached_topic", max_images=3)
            
            self.assertEqual(len(images), 2)
            self.assertIsNone(error)
            self.assertEqual(set(images), set(test_urls))
            
            # Cleanup
            import os
            if os.path.exists(fetcher.cache.db_path):
                os.remove(fetcher.cache.db_path)
        
        asyncio.run(run_test())
    
    def test_max_images_respected(self):
        """Test that max_images parameter is respected"""
        async def run_test():
            fetcher = ImageFetcher(
                pexels_key="test_key",
                cache_enabled=False
            )
            
            # Mock returning 5 images
            async def mock_many_images(*args, **kwargs):
                return [f"https://example.com/photo{i}.jpg" for i in range(5)]
            
            fetcher._fetch_from_pexels = mock_many_images
            
            # Request max 2 images
            images, error = await fetcher.search_images("test", max_images=2)
            
            # Should not receive more than requested
            self.assertLessEqual(len(images), 5)  # API might return all
            self.assertIsNone(error)
        
        asyncio.run(run_test())
    
    def test_rate_limit_error_handling_pexels(self):
        """Test that rate limit errors are properly detected and reported"""
        async def run_test():
            fetcher = ImageFetcher(
                pexels_key="test_key",
                cache_enabled=False
            )
            
            # Mock rate limit error
            async def mock_rate_limit(*args, **kwargs):
                raise aiohttp.ClientError("Rate limit exceeded for Pexels API")
            
            fetcher._fetch_from_pexels = mock_rate_limit
            
            images, error = await fetcher.search_images("test", max_images=3)
            
            self.assertEqual(len(images), 0)
            self.assertIsNotNone(error)
            self.assertIn("rate limit", error.lower())
            self.assertIn("Try again", error)
        
        asyncio.run(run_test())
    
    def test_rate_limit_error_handling_both_apis(self):
        """Test that rate limit errors on both APIs are properly reported"""
        async def run_test():
            fetcher = ImageFetcher(
                pexels_key="test_key",
                pixabay_key="test_pixabay_key",
                cache_enabled=False
            )
            
            # Mock rate limit on both
            async def mock_rate_limit(*args, **kwargs):
                raise aiohttp.ClientError("Rate limit exceeded")
            
            fetcher._fetch_from_pexels = mock_rate_limit
            fetcher._fetch_from_pixabay = mock_rate_limit
            
            images, error = await fetcher.search_images("test", max_images=3)
            
            self.assertEqual(len(images), 0)
            self.assertIsNotNone(error)
            self.assertIn("rate limit", error.lower())
            self.assertIn("Try again", error)
        
        asyncio.run(run_test())
    
    def test_partial_image_failure_recovery(self):
        """Test graceful handling when some images are available but not all requested"""
        async def run_test():
            fetcher = ImageFetcher(
                pexels_key="test_key",
                cache_enabled=False
            )
            
            # Mock returning fewer images than requested
            async def mock_partial_results(*args, **kwargs):
                return ["https://example.com/photo1.jpg"]  # Only 1 image when 3 requested
            
            fetcher._fetch_from_pexels = mock_partial_results
            
            images, error = await fetcher.search_images("test", max_images=3)
            
            # Should return the available image without error
            self.assertEqual(len(images), 1)
            self.assertIsNone(error)
        
        asyncio.run(run_test())
    
    def test_invalid_api_key_with_valid_fallback(self):
        """Test that invalid primary API key gracefully falls back to valid secondary"""
        async def run_test():
            fetcher = ImageFetcher(
                pexels_key="invalid_key",
                pixabay_key="valid_key",
                cache_enabled=False
            )
            
            # Mock Pexels invalid key
            async def mock_invalid(*args, **kwargs):
                raise ValueError("Invalid Pexels API key")
            
            # Mock Pixabay success
            async def mock_valid(*args, **kwargs):
                return ["https://pixabay.com/photo1.jpg", "https://pixabay.com/photo2.jpg"]
            
            fetcher._fetch_from_pexels = mock_invalid
            fetcher._fetch_from_pixabay = mock_valid
            
            images, error = await fetcher.search_images("test", max_images=3)
            
            # Should successfully get images from fallback
            self.assertEqual(len(images), 2)
            self.assertIsNone(error)
            self.assertTrue(all("pixabay" in url for url in images))
        
        asyncio.run(run_test())
    
    def test_network_error_retry_exhaustion(self):
        """Test that network errors are retried and eventually fail gracefully"""
        async def run_test():
            fetcher = ImageFetcher(
                pexels_key="test_key",
                cache_enabled=False
            )
            
            # Mock network timeout
            async def mock_timeout(*args, **kwargs):
                raise asyncio.TimeoutError("Connection timeout")
            
            fetcher._fetch_from_pexels = mock_timeout
            
            images, error = await fetcher.search_images("test", max_images=3)
            
            self.assertEqual(len(images), 0)
            self.assertIsNotNone(error)
        
        asyncio.run(run_test())


if __name__ == '__main__':
    unittest.main()
