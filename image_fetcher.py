"""
Image fetching module for the Telegram bot.
Fetches relevant images from multiple APIs with retry logic, caching, and fallback support.
"""
import os
import logging
import asyncio
import sqlite3
import time
from typing import List, Optional, Tuple
from datetime import datetime, timedelta

import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)


class ImageCache:
    """SQLite-based cache for image URLs with TTL"""
    
    def __init__(self, db_path: str = "image_cache.db", ttl_hours: int = 48):
        self.db_path = db_path
        self.ttl_seconds = ttl_hours * 3600
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS image_cache (
                    keyword TEXT PRIMARY KEY,
                    image_urls TEXT NOT NULL,
                    timestamp INTEGER NOT NULL
                )
            """)
            conn.commit()
    
    def get_cached_images(self, keyword: str) -> Optional[List[str]]:
        """
        Retrieve cached images for a keyword if not expired
        
        Args:
            keyword: Search keyword
            
        Returns:
            List of image URLs or None if not cached or expired
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT image_urls, timestamp FROM image_cache WHERE keyword = ?",
                (keyword.lower(),)
            )
            row = cursor.fetchone()
            
            if row:
                urls_str, timestamp = row
                # Check if cache is still valid
                if time.time() - timestamp < self.ttl_seconds:
                    logger.info(f"Cache HIT for keyword: {keyword}")
                    return urls_str.split('|')
                else:
                    # Clean up expired entry
                    conn.execute("DELETE FROM image_cache WHERE keyword = ?", (keyword.lower(),))
                    conn.commit()
                    logger.info(f"Cache EXPIRED for keyword: {keyword}")
            
            logger.info(f"Cache MISS for keyword: {keyword}")
            return None
    
    def cache_images(self, keyword: str, image_urls: List[str]):
        """
        Cache image URLs for a keyword
        
        Args:
            keyword: Search keyword
            image_urls: List of image URLs to cache
        """
        if not image_urls:
            return
        
        with sqlite3.connect(self.db_path) as conn:
            urls_str = '|'.join(image_urls)
            conn.execute(
                "INSERT OR REPLACE INTO image_cache (keyword, image_urls, timestamp) VALUES (?, ?, ?)",
                (keyword.lower(), urls_str, int(time.time()))
            )
            conn.commit()
            logger.info(f"Cached {len(image_urls)} images for keyword: {keyword}")


class ImageFetcher:
    """
    Fetches images from multiple APIs with retry logic and fallback support
    
    Supports:
    - Pexels API (primary)
    - Pixabay API (fallback)
    - Async operations with aiohttp
    - Retry logic with exponential backoff
    - SQLite caching with 48h TTL
    """
    
    DEFAULT_TIMEOUT = 10  # seconds
    
    def __init__(
        self,
        pexels_key: Optional[str] = None,
        pixabay_key: Optional[str] = None,
        timeout: int = DEFAULT_TIMEOUT,
        cache_enabled: bool = True
    ):
        self.pexels_key = pexels_key or os.getenv("PEXELS_API_KEY")
        self.pixabay_key = pixabay_key or os.getenv("PIXABAY_API_KEY")
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.cache = ImageCache() if cache_enabled else None
        
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=10),
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError))
    )
    async def _fetch_from_pexels(self, query: str, max_images: int) -> List[str]:
        """
        Fetch images from Pexels API with retry logic
        
        Args:
            query: Search query
            max_images: Maximum number of images
            
        Returns:
            List of image URLs
        """
        if not self.pexels_key:
            logger.warning("Pexels API key not configured")
            return []
        
        url = "https://api.pexels.com/v1/search"
        headers = {"Authorization": self.pexels_key}
        params = {
            "query": query,
            "per_page": max_images,
            "orientation": "landscape"
        }
        
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.get(url, headers=headers, params=params) as response:
                response.raise_for_status()
                data = await response.json()
                
                photos = data.get("photos", [])
                image_urls = [
                    photo.get("src", {}).get("large")
                    for photo in photos[:max_images]
                    if photo.get("src", {}).get("large")
                ]
                
                logger.info(f"Pexels: Found {len(image_urls)} images for '{query}'")
                return image_urls
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=10),
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError))
    )
    async def _fetch_from_pixabay(self, query: str, max_images: int) -> List[str]:
        """
        Fetch images from Pixabay API with retry logic (fallback)
        
        Args:
            query: Search query
            max_images: Maximum number of images
            
        Returns:
            List of image URLs
        """
        if not self.pixabay_key:
            logger.warning("Pixabay API key not configured")
            return []
        
        url = "https://pixabay.com/api/"
        params = {
            "key": self.pixabay_key,
            "q": query,
            "per_page": max_images,
            "image_type": "photo",
            "orientation": "horizontal"
        }
        
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.get(url, params=params) as response:
                response.raise_for_status()
                data = await response.json()
                
                hits = data.get("hits", [])
                image_urls = [
                    hit.get("largeImageURL")
                    for hit in hits[:max_images]
                    if hit.get("largeImageURL")
                ]
                
                logger.info(f"Pixabay: Found {len(image_urls)} images for '{query}'")
                return image_urls
    
    async def search_images(self, query: str, max_images: int = 3) -> List[str]:
        """
        Search for images with caching and fallback support
        
        Priority chain:
        1. Check cache (48h TTL)
        2. Try Pexels (3 retries with exponential backoff)
        3. Fallback to Pixabay (3 retries)
        4. Return empty list on complete failure
        
        Args:
            query: Search query
            max_images: Maximum number of images (default 3)
            
        Returns:
            List of image URLs
        """
        # Check cache first
        if self.cache:
            cached = self.cache.get_cached_images(query)
            if cached:
                return cached[:max_images]
        
        image_urls = []
        
        # Try Pexels first
        try:
            image_urls = await self._fetch_from_pexels(query, max_images)
            if image_urls:
                if self.cache:
                    self.cache.cache_images(query, image_urls)
                return image_urls
        except Exception as e:
            logger.warning(f"Pexels fetch failed: {e}. Trying fallback...")
        
        # Fallback to Pixabay
        try:
            image_urls = await self._fetch_from_pixabay(query, max_images)
            if image_urls:
                if self.cache:
                    self.cache.cache_images(query, image_urls)
                return image_urls
        except Exception as e:
            logger.error(f"All image sources failed for '{query}': {e}")
        
        return []
    
    def search_images_sync(self, query: str, max_images: int = 3) -> List[str]:
        """
        Synchronous wrapper for search_images (for compatibility)
        
        Args:
            query: Search query
            max_images: Maximum number of images
            
        Returns:
            List of image URLs
        """
        try:
            # Try to get existing event loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is already running, create task
                future = asyncio.ensure_future(self.search_images(query, max_images))
                return []  # Can't wait in running loop, return empty
            else:
                # Run in existing loop
                return loop.run_until_complete(self.search_images(query, max_images))
        except RuntimeError:
            # No event loop, create new one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(self.search_images(query, max_images))
            finally:
                loop.close()


# Global instance
image_fetcher = ImageFetcher()
