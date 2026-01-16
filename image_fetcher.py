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
            
        Raises:
            ValueError: If API key is not configured
            aiohttp.ClientError: If API request fails
        """
        if not self.pexels_key:
            logger.warning("Pexels API key not configured")
            raise ValueError("Pexels API key not configured")
        
        url = "https://api.pexels.com/v1/search"
        headers = {"Authorization": self.pexels_key}
        params = {
            "query": query,
            "per_page": max_images,
            "orientation": "landscape"
        }
        
        logger.debug(f"Pexels API request: query='{query}', max_images={max_images}")
        
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.get(url, headers=headers, params=params) as response:
                status = response.status
                logger.debug(f"Pexels API response: status={status}, query='{query}'")
                
                if status == 401:
                    logger.error("Pexels API: Invalid API key (401 Unauthorized)")
                    raise ValueError("Invalid Pexels API key")
                
                if status == 429:
                    logger.warning(f"Pexels API: Rate limit exceeded (429 Too Many Requests) for query '{query}'")
                    raise aiohttp.ClientError(f"Rate limit exceeded for Pexels API")
                
                response.raise_for_status()
                data = await response.json()
                
                photos = data.get("photos", [])
                if not photos:
                    logger.info(f"Pexels: No images found for '{query}'")
                    return []
                
                image_urls = [
                    photo.get("src", {}).get("large")
                    for photo in photos[:max_images]
                    if photo.get("src", {}).get("large")
                ]
                
                logger.info(f"Pexels: Found {len(image_urls)} images for '{query}'")
                if image_urls:
                    logger.debug(f"Pexels image URLs: {image_urls}")
                
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
            
        Raises:
            ValueError: If API key is not configured
            aiohttp.ClientError: If API request fails
        """
        if not self.pixabay_key:
            logger.warning("Pixabay API key not configured")
            raise ValueError("Pixabay API key not configured")
        
        url = "https://pixabay.com/api/"
        params = {
            "key": self.pixabay_key,
            "q": query,
            "per_page": max_images,
            "image_type": "photo",
            "orientation": "horizontal"
        }
        
        logger.debug(f"Pixabay API request: query='{query}', max_images={max_images}")
        
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.get(url, params=params) as response:
                status = response.status
                logger.debug(f"Pixabay API response: status={status}, query='{query}'")
                
                if status == 401:
                    logger.error("Pixabay API: Invalid API key (401 Unauthorized)")
                    raise ValueError("Invalid Pixabay API key")
                
                if status == 429:
                    logger.warning(f"Pixabay API: Rate limit exceeded (429 Too Many Requests) for query '{query}'")
                    raise aiohttp.ClientError(f"Rate limit exceeded for Pixabay API")
                
                response.raise_for_status()
                data = await response.json()
                
                hits = data.get("hits", [])
                if not hits:
                    logger.info(f"Pixabay: No images found for '{query}'")
                    return []
                
                image_urls = [
                    hit.get("largeImageURL")
                    for hit in hits[:max_images]
                    if hit.get("largeImageURL")
                ]
                
                logger.info(f"Pixabay: Found {len(image_urls)} images for '{query}'")
                if image_urls:
                    logger.debug(f"Pixabay image URLs: {image_urls}")
                
                return image_urls
    
    async def search_images(self, query: str, max_images: int = 3) -> Tuple[List[str], Optional[str]]:
        """
        Search for images with caching and fallback support
        
        Priority chain:
        1. Check cache (48h TTL)
        2. Try Pexels (3 retries with exponential backoff)
        3. Fallback to Pixabay (3 retries)
        4. Return empty list with error message on complete failure
        
        Args:
            query: Search query
            max_images: Maximum number of images (default 3)
            
        Returns:
            Tuple of (list of image URLs, optional error message)
        """
        logger.info(f"Searching images for query='{query}', max_images={max_images}")
        
        # Check cache first
        if self.cache:
            cached = self.cache.get_cached_images(query)
            if cached:
                logger.info(f"Returning {len(cached[:max_images])} cached images for '{query}'")
                return cached[:max_images], None
        
        image_urls = []
        error_msg = None
        rate_limited = False
        
        # Try Pexels first
        try:
            image_urls = await self._fetch_from_pexels(query, max_images)
            if image_urls:
                if self.cache:
                    self.cache.cache_images(query, image_urls)
                logger.info(f"Successfully fetched {len(image_urls)} images from Pexels for '{query}'")
                return image_urls, None
            else:
                error_msg = "No results from Pexels API"
                logger.warning(f"Pexels returned no images for '{query}'")
        except ValueError as e:
            # API key not configured or invalid
            error_msg = str(e)
            logger.warning(f"Pexels fetch failed: {e}. Trying fallback...")
        except aiohttp.ClientError as e:
            error_details = str(e)
            if "Rate limit" in error_details or "429" in error_details:
                rate_limited = True
                error_msg = "Pexels API rate limit exceeded"
                logger.warning(f"Pexels rate limited for '{query}'. Trying fallback...")
            else:
                error_msg = f"Pexels API error: {type(e).__name__}"
                logger.warning(f"Pexels fetch failed with {type(e).__name__}: {e}. Trying fallback...")
        except Exception as e:
            error_msg = f"Pexels API error: {type(e).__name__}"
            logger.warning(f"Pexels fetch failed: {e}. Trying fallback...")
        
        # Fallback to Pixabay
        try:
            image_urls = await self._fetch_from_pixabay(query, max_images)
            if image_urls:
                if self.cache:
                    self.cache.cache_images(query, image_urls)
                logger.info(f"Successfully fetched {len(image_urls)} images from Pixabay (fallback) for '{query}'")
                return image_urls, None
            else:
                error_msg = f"{error_msg}; No results from Pixabay API" if error_msg else "No results from Pixabay API"
                logger.warning(f"Pixabay returned no images for '{query}'")
        except ValueError as e:
            # API key not configured or invalid
            error_msg = f"{error_msg}; {str(e)}" if error_msg else str(e)
            logger.error(f"All image sources failed for '{query}': {error_msg}")
        except aiohttp.ClientError as e:
            error_details = str(e)
            if "Rate limit" in error_details or "429" in error_details:
                rate_limited = True
                error_msg = f"{error_msg}; Pixabay API rate limit exceeded" if error_msg else "Pixabay API rate limit exceeded"
                logger.error(f"Both APIs rate limited for '{query}'")
            else:
                error_msg = f"{error_msg}; Pixabay API error: {type(e).__name__}" if error_msg else f"Pixabay API error: {type(e).__name__}"
                logger.error(f"Pixabay fallback failed with {type(e).__name__}: {e}")
        except Exception as e:
            error_msg = f"{error_msg}; Pixabay API error: {type(e).__name__}" if error_msg else f"Pixabay API error: {type(e).__name__}"
            logger.error(f"All image sources failed for '{query}': {e}")
        
        # Add rate limit hint to error message
        if rate_limited and error_msg:
            error_msg = f"{error_msg}. Try again in a few minutes."
        
        logger.error(f"Image search failed for '{query}': {error_msg}")
        return [], error_msg


# Global instance
image_fetcher = ImageFetcher()
