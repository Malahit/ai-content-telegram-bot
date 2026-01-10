"""
Tests for image fetcher module
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from image_fetcher import ImageFetcher, RateLimiter


@pytest.fixture
def image_fetcher():
    """Create an ImageFetcher instance for testing"""
    return ImageFetcher(
        unsplash_key="test_unsplash_key",
        pexels_key="test_pexels_key",
        pixabay_key="test_pixabay_key"
    )


@pytest.mark.asyncio
async def test_rate_limiter_allows_calls():
    """Test that rate limiter allows calls within limit"""
    limiter = RateLimiter(max_calls=5, period=60)
    
    # Should allow 5 calls without waiting
    for _ in range(5):
        await limiter.wait_if_needed()


@pytest.mark.asyncio
async def test_rate_limiter_blocks_excess_calls():
    """Test that rate limiter blocks calls exceeding limit"""
    limiter = RateLimiter(max_calls=2, period=1)
    
    # First 2 calls should be fast
    start_time = asyncio.get_event_loop().time()
    await limiter.wait_if_needed()
    await limiter.wait_if_needed()
    
    # Third call should wait
    await limiter.wait_if_needed()
    end_time = asyncio.get_event_loop().time()
    
    # Should have waited approximately 1 second
    assert end_time - start_time >= 0.9


@pytest.mark.asyncio
async def test_fetch_image_with_cache(image_fetcher):
    """Test fetch_image uses cache"""
    with patch('image_fetcher.image_cache') as mock_cache:
        # Mock cache hit
        mock_cache.get_cached_image.return_value = "https://cached.com/image.jpg"
        
        url = await image_fetcher.fetch_image("test query")
        
        assert url == "https://cached.com/image.jpg"
        mock_cache.get_cached_image.assert_called_once_with("test query")


@pytest.mark.asyncio
async def test_search_images_fallback_to_pexels(image_fetcher):
    """Test that search_images falls back to Pexels when Unsplash fails"""
    # Mock Unsplash failure
    with patch.object(image_fetcher, '_fetch_from_unsplash', side_effect=Exception("Unsplash failed")):
        # Mock Pexels success
        with patch.object(image_fetcher, '_fetch_from_pexels', return_value=["https://pexels.com/photo1"]):
            with patch('image_fetcher.image_cache') as mock_cache:
                urls = await image_fetcher.search_images("test query")
                
                assert len(urls) == 1
                assert urls[0] == "https://pexels.com/photo1"
                # Should cache the result
                mock_cache.cache_image.assert_called_once()


@pytest.mark.asyncio
async def test_search_images_fallback_to_pixabay(image_fetcher):
    """Test that search_images falls back to Pixabay when Unsplash and Pexels fail"""
    # Mock Unsplash failure
    with patch.object(image_fetcher, '_fetch_from_unsplash', side_effect=Exception("Unsplash failed")):
        # Mock Pexels failure
        with patch.object(image_fetcher, '_fetch_from_pexels', return_value=[]):
            # Mock Pixabay success
            with patch.object(image_fetcher, '_fetch_from_pixabay', return_value=["https://pixabay.com/photo1"]):
                with patch('image_fetcher.image_cache') as mock_cache:
                    urls = await image_fetcher.search_images("test query")
                    
                    assert len(urls) == 1
                    assert urls[0] == "https://pixabay.com/photo1"


@pytest.mark.asyncio
async def test_search_images_all_sources_fail(image_fetcher):
    """Test that search_images returns empty list when all sources fail"""
    # Mock all sources failing
    with patch.object(image_fetcher, '_fetch_from_unsplash', side_effect=Exception("Failed")):
        with patch.object(image_fetcher, '_fetch_from_pexels', return_value=[]):
            with patch.object(image_fetcher, '_fetch_from_pixabay', return_value=[]):
                urls = await image_fetcher.search_images("test query")
                
                assert urls == []


@pytest.mark.asyncio
async def test_fetch_image_no_cache_uses_unsplash(image_fetcher):
    """Test fetch_image calls Unsplash when cache misses"""
    with patch('image_fetcher.image_cache') as mock_cache:
        # Mock cache miss
        mock_cache.get_cached_image.return_value = None
        
        # Mock successful Unsplash fetch
        with patch.object(image_fetcher, '_fetch_from_unsplash', return_value=["https://unsplash.com/photo1"]):
            url = await image_fetcher.fetch_image("test query")
            
            assert url == "https://unsplash.com/photo1"
            # Should cache the result
            mock_cache.cache_image.assert_called_once_with("test query", "https://unsplash.com/photo1")


@pytest.mark.asyncio
async def test_fetch_image_fallback_chain(image_fetcher):
    """Test fetch_image falls back through all sources"""
    with patch('image_fetcher.image_cache') as mock_cache:
        # Mock cache miss
        mock_cache.get_cached_image.return_value = None
        
        # Mock Unsplash failure
        with patch.object(image_fetcher, '_fetch_from_unsplash', side_effect=Exception("Failed")):
            # Mock Pexels failure
            with patch.object(image_fetcher, '_fetch_from_pexels', return_value=[]):
                # Mock Pixabay success
                with patch.object(image_fetcher, '_fetch_from_pixabay', return_value=["https://pixabay.com/photo1"]):
                    url = await image_fetcher.fetch_image("test query")
                    
                    assert url == "https://pixabay.com/photo1"
                    mock_cache.cache_image.assert_called_once()

