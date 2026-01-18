"""
Unit tests for /generate command with image support.
"""
import unittest
import asyncio
import sys
import os
from unittest.mock import Mock, AsyncMock, patch, MagicMock

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestGenerateCommand(unittest.TestCase):
    """Test /generate command functionality"""
    
    def test_image_fetcher_integration(self):
        """Test that ImageFetcher can be imported and instantiated"""
        async def run_test():
            from services.image_fetcher import ImageFetcher
            
            # Test instantiation
            fetcher = ImageFetcher(pexels_key="test_key")
            self.assertIsNotNone(fetcher)
            
            # Test methods exist
            self.assertTrue(hasattr(fetcher, 'fetch_images'))
            self.assertTrue(hasattr(fetcher, 'search_images'))
            
            # Test fetch_images signature
            # Mock the search_images method to avoid actual API calls
            async def mock_search(*args, **kwargs):
                return ["https://example.com/image1.jpg"], None
            
            fetcher.search_images = mock_search
            
            # Test fetch_images
            images = await fetcher.fetch_images("test topic", num_images=1)
            self.assertEqual(len(images), 1)
            self.assertIn("example.com", images[0])
        
        asyncio.run(run_test())
    
    def test_fetch_images_empty_result(self):
        """Test that fetch_images handles empty results correctly"""
        async def run_test():
            from services.image_fetcher import ImageFetcher
            
            fetcher = ImageFetcher(pexels_key="test_key")
            
            # Mock search_images to return empty list
            async def mock_search(*args, **kwargs):
                return [], "No results found"
            
            fetcher.search_images = mock_search
            
            # Test fetch_images with no results
            images = await fetcher.fetch_images("nonexistent topic", num_images=1)
            self.assertEqual(len(images), 0)
        
        asyncio.run(run_test())
    
    def test_statistics_recording_signature(self):
        """Test that bot_statistics.record_post has the expected signature"""
        try:
            from bot_statistics import stats_tracker
            
            # Verify the method exists
            self.assertTrue(hasattr(stats_tracker, 'record_post'))
            
            # Test that it can be called with expected parameters
            # (we're not actually calling it to avoid modifying test state)
            import inspect
            sig = inspect.signature(stats_tracker.record_post)
            params = list(sig.parameters.keys())
            
            # Should have user_id, topic, and post_type parameters
            self.assertIn('user_id', params)
            self.assertIn('topic', params)
            self.assertIn('post_type', params)
            
            print("✅ Statistics tracker has correct signature")
        except ImportError:
            # If bot_statistics is not available, skip this test
            self.skipTest("bot_statistics module not available")


if __name__ == '__main__':
    unittest.main(verbosity=2)
