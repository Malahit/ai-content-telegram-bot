"""
Test suite for image_fetcher module
Tests caching, fallback, and retry functionality
"""
import asyncio
import os
import aiosqlite
from unittest.mock import Mock, patch, AsyncMock
from image_fetcher import ImageFetcher
import logging

# Configure logging for tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_cache_initialization():
    """Test that cache database is properly initialized"""
    print("\n🧪 Test 1: Cache Initialization")
    
    # Clean up any existing test database
    test_db = "test_image_cache.db"
    if os.path.exists(test_db):
        os.remove(test_db)
    
    fetcher = ImageFetcher()
    fetcher.DB_PATH = test_db
    
    await fetcher._init_db()
    
    # Verify table exists
    async with aiosqlite.connect(test_db) as db:
        cursor = await db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='image_cache'"
        )
        result = await cursor.fetchone()
        assert result is not None, "Cache table should exist"
    
    print("✅ Cache initialized successfully")
    
    # Cleanup
    os.remove(test_db)


async def test_cache_storage_and_retrieval():
    """Test caching images and retrieving them"""
    print("\n🧪 Test 2: Cache Storage and Retrieval")
    
    test_db = "test_image_cache.db"
    if os.path.exists(test_db):
        os.remove(test_db)
    
    fetcher = ImageFetcher()
    fetcher.DB_PATH = test_db
    
    keyword = "test_fitness"
    image_urls = [
        "https://example.com/image1.jpg",
        "https://example.com/image2.jpg",
        "https://example.com/image3.jpg"
    ]
    
    # Cache images
    await fetcher._cache_images(keyword, image_urls)
    print(f"   Cached {len(image_urls)} images")
    
    # Retrieve from cache
    cached = await fetcher._get_cached_images(keyword, max_images=3)
    print(f"   Retrieved {len(cached)} images from cache")
    
    assert len(cached) == len(image_urls), f"Expected {len(image_urls)} images, got {len(cached)}"
    assert set(cached) == set(image_urls), "Cached images should match original"
    
    print("✅ Cache storage and retrieval works correctly")
    
    # Cleanup
    os.remove(test_db)


async def test_cache_miss():
    """Test cache miss for non-existent keyword"""
    print("\n🧪 Test 3: Cache Miss")
    
    test_db = "test_image_cache.db"
    if os.path.exists(test_db):
        os.remove(test_db)
    
    fetcher = ImageFetcher()
    fetcher.DB_PATH = test_db
    
    # Try to get images for non-existent keyword
    cached = await fetcher._get_cached_images("nonexistent_keyword")
    
    assert len(cached) == 0, "Should return empty list for cache miss"
    print("✅ Cache miss handled correctly")
    
    # Cleanup
    if os.path.exists(test_db):
        os.remove(test_db)


async def test_fallback_to_pexels():
    """Test fallback from Unsplash to Pexels"""
    print("\n🧪 Test 4: Fallback to Pexels")
    
    test_db = "test_image_cache.db"
    if os.path.exists(test_db):
        os.remove(test_db)
    
    fetcher = ImageFetcher(
        unsplash_key="fake_key",
        pexels_key="fake_pexels_key"
    )
    fetcher.DB_PATH = test_db
    
    # Mock Unsplash to fail and Pexels to succeed
    async def mock_unsplash_fail(*args, **kwargs):
        raise Exception("Unsplash API error")
    
    async def mock_pexels_success(*args, **kwargs):
        return ["https://pexels.com/photo1.jpg", "https://pexels.com/photo2.jpg"]
    
    fetcher._fetch_from_unsplash = mock_unsplash_fail
    fetcher._fetch_from_pexels = mock_pexels_success
    
    images = await fetcher.search_images("test", max_images=3)
    
    assert len(images) > 0, "Should get images from Pexels fallback"
    assert "pexels" in images[0], "Images should be from Pexels"
    print(f"✅ Fallback to Pexels successful: {len(images)} images")
    
    # Cleanup
    if os.path.exists(test_db):
        os.remove(test_db)


async def test_fallback_to_pixabay():
    """Test fallback from Unsplash and Pexels to Pixabay"""
    print("\n🧪 Test 5: Fallback to Pixabay")
    
    test_db = "test_image_cache.db"
    if os.path.exists(test_db):
        os.remove(test_db)
    
    fetcher = ImageFetcher(
        unsplash_key="fake_key",
        pexels_key="fake_pexels_key",
        pixabay_key="fake_pixabay_key"
    )
    fetcher.DB_PATH = test_db
    
    # Mock both Unsplash and Pexels to fail, Pixabay to succeed
    async def mock_fail(*args, **kwargs):
        raise Exception("API error")
    
    async def mock_pixabay_success(*args, **kwargs):
        return ["https://pixabay.com/photo1.jpg"]
    
    fetcher._fetch_from_unsplash = mock_fail
    fetcher._fetch_from_pexels = mock_fail
    fetcher._fetch_from_pixabay = mock_pixabay_success
    
    images = await fetcher.search_images("test", max_images=3)
    
    assert len(images) > 0, "Should get images from Pixabay fallback"
    assert "pixabay" in images[0], "Images should be from Pixabay"
    print(f"✅ Fallback to Pixabay successful: {len(images)} images")
    
    # Cleanup
    if os.path.exists(test_db):
        os.remove(test_db)


async def test_all_apis_fail():
    """Test behavior when all APIs fail"""
    print("\n🧪 Test 6: All APIs Fail")
    
    test_db = "test_image_cache.db"
    if os.path.exists(test_db):
        os.remove(test_db)
    
    fetcher = ImageFetcher(
        unsplash_key="fake_key",
        pexels_key="fake_pexels_key",
        pixabay_key="fake_pixabay_key"
    )
    fetcher.DB_PATH = test_db
    
    # Mock all APIs to fail
    async def mock_fail(*args, **kwargs):
        raise Exception("API error")
    
    fetcher._fetch_from_unsplash = mock_fail
    fetcher._fetch_from_pexels = mock_fail
    fetcher._fetch_from_pixabay = mock_fail
    
    images = await fetcher.search_images("test", max_images=3)
    
    assert len(images) == 0, "Should return empty list when all APIs fail"
    print("✅ All APIs fail handled correctly")
    
    # Cleanup
    if os.path.exists(test_db):
        os.remove(test_db)


async def test_cache_hit_avoids_api_call():
    """Test that cached images avoid API calls"""
    print("\n🧪 Test 7: Cache Hit Avoids API Call")
    
    test_db = "test_image_cache.db"
    if os.path.exists(test_db):
        os.remove(test_db)
    
    fetcher = ImageFetcher(unsplash_key="fake_key")
    fetcher.DB_PATH = test_db
    
    keyword = "cached_topic"
    image_urls = ["https://example.com/cached1.jpg"]
    
    # Pre-populate cache
    await fetcher._cache_images(keyword, image_urls)
    
    # Mock API call tracker
    api_called = False
    
    async def mock_api_call(*args, **kwargs):
        nonlocal api_called
        api_called = True
        return []
    
    fetcher._fetch_from_unsplash = mock_api_call
    
    # Fetch images (should come from cache)
    images = await fetcher.search_images(keyword, max_images=3)
    
    assert len(images) > 0, "Should get images from cache"
    assert not api_called, "API should not be called when cache hit"
    print("✅ Cache hit successfully avoided API call")
    
    # Cleanup
    if os.path.exists(test_db):
        os.remove(test_db)


async def test_no_api_keys():
    """Test behavior when no API keys are configured"""
    print("\n🧪 Test 8: No API Keys")
    
    test_db = "test_image_cache.db"
    if os.path.exists(test_db):
        os.remove(test_db)
    
    # Create fetcher with no API keys
    fetcher = ImageFetcher()
    fetcher.DB_PATH = test_db
    fetcher.unsplash_key = None
    fetcher.pexels_key = None
    fetcher.pixabay_key = None
    
    images = await fetcher.search_images("test", max_images=3)
    
    assert len(images) == 0, "Should return empty list when no API keys"
    print("✅ No API keys handled correctly")
    
    # Cleanup
    if os.path.exists(test_db):
        os.remove(test_db)


async def run_all_tests():
    """Run all tests"""
    print("=" * 60)
    print("Running Image Fetcher Test Suite")
    print("=" * 60)
    
    try:
        await test_cache_initialization()
        await test_cache_storage_and_retrieval()
        await test_cache_miss()
        await test_fallback_to_pexels()
        await test_fallback_to_pixabay()
        await test_all_apis_fail()
        await test_cache_hit_avoids_api_call()
        await test_no_api_keys()
        
        print("\n" + "=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        raise
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(run_all_tests())
