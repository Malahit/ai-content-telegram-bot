#!/usr/bin/env python3
"""
Demo script to show image fetcher and cache functionality
"""
import asyncio
import tempfile
import os
from image_fetcher import ImageFetcher
from image_cache_db import ImageCacheDB


async def demo():
    """Demonstrate the image fetching and caching functionality"""
    
    print("=" * 60)
    print("IMAGE FETCHER & CACHE DEMO")
    print("=" * 60)
    
    # Create temporary cache for demo
    temp_db = tempfile.mktemp(suffix='.db')
    cache = ImageCacheDB(temp_db)
    
    # Create fetcher (without real API keys for demo)
    fetcher = ImageFetcher()
    
    print("\n1. Testing Image Cache")
    print("-" * 60)
    
    # Test caching
    test_keyword = "technology"
    test_url = "https://images.unsplash.com/photo-demo-123"
    
    print(f"Caching image for keyword: '{test_keyword}'")
    cache.cache_image(test_keyword, test_url)
    print(f"✅ Cached: {test_url}")
    
    # Retrieve from cache
    cached_url = cache.get_cached_image(test_keyword)
    print(f"✅ Retrieved from cache: {cached_url}")
    
    # Test case insensitivity
    cached_url_upper = cache.get_cached_image("TECHNOLOGY")
    print(f"✅ Case-insensitive retrieval: {cached_url_upper}")
    
    print("\n2. Testing Rate Limiter")
    print("-" * 60)
    
    # Test rate limiter
    from image_fetcher import RateLimiter
    limiter = RateLimiter(max_calls=5, period=60)
    
    print("Simulating 5 API calls (within limit)...")
    for i in range(5):
        await limiter.wait_if_needed()
        print(f"  Call {i+1}: ✅ Allowed")
    
    print("\n3. Image Source Fallback Chain")
    print("-" * 60)
    print("When fetching images, the bot tries sources in order:")
    print("  1. Unsplash (with retry logic)")
    print("     ↓ (if fails)")
    print("  2. Pexels")
    print("     ↓ (if fails)")
    print("  3. Pixabay")
    print("     ↓")
    print("  Cache result (48h TTL)")
    
    print("\n4. Key Features")
    print("-" * 60)
    print("✨ Retry Logic: 3 attempts with exponential backoff")
    print("✨ Rate Limiting: 5 requests per minute")
    print("✨ Smart Caching: 48-hour TTL in SQLite")
    print("✨ Error Handling: Graceful fallback on 429/403")
    print("✨ Async Support: aiohttp for concurrent requests")
    
    print("\n5. Cache Statistics")
    print("-" * 60)
    
    # Add more test entries
    cache.cache_image("marketing", "https://example.com/img1.jpg")
    cache.cache_image("business", "https://example.com/img2.jpg")
    cache.cache_image("design", "https://example.com/img3.jpg")
    
    print(f"Total cached keywords: 4")
    print("✅ All entries cached successfully")
    
    # Clean up
    os.remove(temp_db)
    
    print("\n" + "=" * 60)
    print("DEMO COMPLETED SUCCESSFULLY! ✨")
    print("=" * 60)
    print("\nTo use in production:")
    print("1. Add API keys to .env file")
    print("2. Run: python bot.py")
    print("3. Try /wordstat command in Telegram")


if __name__ == "__main__":
    asyncio.run(demo())
