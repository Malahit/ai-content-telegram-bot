#!/usr/bin/env python3
"""
Unit tests for image_fetcher module.
Tests async image fetching with retry, fallback, and caching functionality.
"""
import asyncio
import os
import sys
import tempfile
import logging

# Add parent directory to path to allow direct import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import directly from the module to avoid services package dependencies
from services.image_fetcher import ImageFetcher, ImageCache

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_test_db_path():
    """Get a temporary test database path"""
    fd, path = tempfile.mkstemp(suffix=".db", prefix="test_cache_")
    os.close(fd)  # Close the file descriptor, we just need the path
    return path


def cleanup_test_db(db_path):
    """Clean up test database file"""
    try:
        if os.path.exists(db_path):
            os.remove(db_path)
    except Exception as e:
        logger.warning(f"Failed to cleanup test db {db_path}: {e}")


async def test_cache_initialization():
    """Test that cache database is properly initialized"""
    print("\n🧪 Test 1: Cache Initialization")
    
    test_db = get_test_db_path()
    
    try:
        cache = ImageCache(db_path=test_db, ttl_hours=48)
        
        # Verify database file was created
        assert os.path.exists(test_db), "Cache database should be created"
        print("✅ Cache initialized successfully")
    finally:
        cleanup_test_db(test_db)


async def test_cache_storage_and_retrieval():
    """Test caching images and retrieving them"""
    print("\n🧪 Test 2: Cache Storage and Retrieval")
    
    test_db = get_test_db_path()
    
    try:
        cache = ImageCache(db_path=test_db, ttl_hours=48)
        
        keyword = "test_fitness"
        image_urls = [
            "https://example.com/image1.jpg",
            "https://example.com/image2.jpg",
            "https://example.com/image3.jpg"
        ]
        
        # Cache images
        cache.cache_images(keyword, image_urls)
        print(f"   Cached {len(image_urls)} images")
        
        # Retrieve from cache
        cached = cache.get_cached_images(keyword)
        print(f"   Retrieved {len(cached)} images from cache")
        
        assert len(cached) == len(image_urls), f"Expected {len(image_urls)} images, got {len(cached)}"
        assert set(cached) == set(image_urls), "Cached images should match original"
        
        print("✅ Cache storage and retrieval works correctly")
    finally:
        cleanup_test_db(test_db)


async def test_cache_miss():
    """Test cache miss for non-existent keyword"""
    print("\n🧪 Test 3: Cache Miss")
    
    test_db = get_test_db_path()
    
    try:
        cache = ImageCache(db_path=test_db, ttl_hours=48)
        
        # Try to get images for non-existent keyword
        cached = cache.get_cached_images("nonexistent_keyword")
        
        assert cached is None, "Should return None for cache miss"
        print("✅ Cache miss handled correctly")
    finally:
        cleanup_test_db(test_db)


async def test_fetcher_initialization():
    """Test ImageFetcher initialization with API keys"""
    print("\n🧪 Test 4: ImageFetcher Initialization")
    
    # Test with Pexels key
    fetcher = ImageFetcher(pexels_key="test_pexels_key", cache_enabled=False)
    assert fetcher.pexels_key == "test_pexels_key"
    
    # Test with Pixabay key
    fetcher = ImageFetcher(pixabay_key="test_pixabay_key", cache_enabled=False)
    assert fetcher.pixabay_key == "test_pixabay_key"
    
    # Test with both keys
    fetcher = ImageFetcher(
        pexels_key="test_pexels_key",
        pixabay_key="test_pixabay_key",
        cache_enabled=False
    )
    assert fetcher.pexels_key == "test_pexels_key"
    assert fetcher.pixabay_key == "test_pixabay_key"
    
    print("✅ ImageFetcher initialized correctly")


async def test_fallback_to_pixabay():
    """Test fallback from Pexels to Pixabay"""
    print("\n🧪 Test 5: Fallback to Pixabay")
    
    fetcher = ImageFetcher(
        pexels_key="fake_pexels_key",
        pixabay_key="fake_pixabay_key",
        cache_enabled=False
    )
    
    # Mock Pexels to fail and Pixabay to succeed
    async def mock_pexels_fail(*args, **kwargs):
        raise Exception("Pexels API error")
    
    async def mock_pixabay_success(*args, **kwargs):
        return ["https://pixabay.com/photo1.jpg", "https://pixabay.com/photo2.jpg"]
    
    fetcher._fetch_from_pexels = mock_pexels_fail
    fetcher._fetch_from_pixabay = mock_pixabay_success
    
    images, error_msg = await fetcher.search_images("test", max_images=3)
    
    assert len(images) > 0, "Should get images from Pixabay fallback"
    assert "pixabay" in images[0], "Images should be from Pixabay"
    assert error_msg is None, "Should not have error message on success"
    print(f"✅ Fallback to Pixabay successful: {len(images)} images")


async def test_all_apis_fail():
    """Test behavior when all APIs fail"""
    print("\n🧪 Test 6: All APIs Fail")
    
    fetcher = ImageFetcher(
        pexels_key="fake_pexels_key",
        pixabay_key="fake_pixabay_key",
        cache_enabled=False
    )
    
    # Mock all APIs to fail
    async def mock_fail(*args, **kwargs):
        raise Exception("API error")
    
    fetcher._fetch_from_pexels = mock_fail
    fetcher._fetch_from_pixabay = mock_fail
    
    images, error_msg = await fetcher.search_images("test", max_images=3)
    
    assert len(images) == 0, "Should return empty list when all APIs fail"
    assert error_msg is not None, "Should have error message when all APIs fail"
    print(f"✅ All APIs fail handled correctly (error: {error_msg})")


async def test_no_api_keys():
    """Test behavior when no API keys are configured"""
    print("\n🧪 Test 7: No API Keys")
    
    fetcher = ImageFetcher(cache_enabled=False)
    
    images, error_msg = await fetcher.search_images("test", max_images=3)
    
    assert len(images) == 0, "Should return empty list when no API keys configured"
    assert error_msg is not None, "Should have error message when no API keys"
    assert "not configured" in error_msg.lower(), "Error message should mention API key issue"
    print(f"✅ No API keys handled correctly (error: {error_msg})")


async def run_all_tests():
    """Run all async tests"""
    print("=" * 60)
    print("Running Image Fetcher Tests")
    print("=" * 60)
    
    tests = [
        test_cache_initialization,
        test_cache_storage_and_retrieval,
        test_cache_miss,
        test_fetcher_initialization,
        test_fallback_to_pixabay,
        test_all_apis_fail,
        test_no_api_keys,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            await test()
            passed += 1
        except AssertionError as e:
            print(f"❌ {test.__name__} failed: {e}")
            failed += 1
        except Exception as e:
            print(f"❌ {test.__name__} error: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == '__main__':
    # Run async tests
    success = asyncio.run(run_all_tests())
    exit(0 if success else 1)
