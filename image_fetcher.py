"""
Image fetching module for the Telegram bot.
Fetches relevant images from Unsplash, Pexels, or Pixabay APIs with caching and fallback support.
"""
import os
import logging
import aiohttp
import aiosqlite
import asyncio
from typing import List, Optional
from datetime import datetime, timedelta
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)


class ImageFetcher:
    """Fetches images from multiple APIs with caching and fallback support"""
    
    # Configuration constants
    DEFAULT_TIMEOUT = 10  # seconds
    CACHE_TTL_HOURS = 48  # Cache time-to-live
    DB_PATH = "image_cache.db"
    
    def __init__(
        self,
        unsplash_key: Optional[str] = None,
        pexels_key: Optional[str] = None,
        pixabay_key: Optional[str] = None,
        timeout: int = DEFAULT_TIMEOUT
    ):
        self.unsplash_key = unsplash_key or os.getenv("UNSPLASH_API_KEY")
        self.pexels_key = pexels_key or os.getenv("PEXELS_API_KEY")
        self.pixabay_key = pixabay_key or os.getenv("PIXABAY_API_KEY")
        self.timeout = timeout
        self._db_initialized = False
    
    async def _init_db(self):
        """Initialize SQLite database for caching"""
        if self._db_initialized:
            return
        
        try:
            async with aiosqlite.connect(self.DB_PATH) as db:
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS image_cache (
                        keyword TEXT NOT NULL,
                        image_url TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        PRIMARY KEY (keyword, image_url)
                    )
                """)
                await db.commit()
            self._db_initialized = True
            logger.info("Image cache database initialized")
        except Exception as e:
            logger.error(f"Failed to initialize cache database: {e}")
    
    async def _get_cached_images(self, keyword: str, max_images: int = 3) -> List[str]:
        """Get cached images for a keyword if they exist and are not expired"""
        await self._init_db()
        
        try:
            cutoff_time = (datetime.utcnow() - timedelta(hours=self.CACHE_TTL_HOURS)).isoformat()
            
            async with aiosqlite.connect(self.DB_PATH) as db:
                cursor = await db.execute(
                    "SELECT image_url FROM image_cache WHERE keyword = ? AND timestamp > ? LIMIT ?",
                    (keyword, cutoff_time, max_images)
                )
                rows = await cursor.fetchall()
                
                if rows:
                    images = [row[0] for row in rows]
                    logger.info(f"Cache HIT: Found {len(images)} cached images for '{keyword}'")
                    return images
                else:
                    logger.info(f"Cache MISS: No cached images for '{keyword}'")
                    return []
        except Exception as e:
            logger.error(f"Error reading from cache: {e}")
            return []
    
    async def _cache_images(self, keyword: str, image_urls: List[str]):
        """Cache images for a keyword"""
        await self._init_db()
        
        try:
            timestamp = datetime.utcnow().isoformat()
            async with aiosqlite.connect(self.DB_PATH) as db:
                for url in image_urls:
                    await db.execute(
                        "INSERT OR REPLACE INTO image_cache (keyword, image_url, timestamp) VALUES (?, ?, ?)",
                        (keyword, url, timestamp)
                    )
                await db.commit()
            logger.info(f"Cached {len(image_urls)} images for '{keyword}'")
        except Exception as e:
            logger.error(f"Error caching images: {e}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)),
        reraise=True
    )
    async def _fetch_from_unsplash(self, query: str, max_images: int = 3) -> List[str]:
        """Fetch images from Unsplash API with retry logic"""
        if not self.unsplash_key:
            logger.warning("Unsplash API key not configured")
            return []
        
        logger.info(f"Attempting to fetch images from Unsplash for '{query}'")
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Client-ID {self.unsplash_key}",
                    "Accept-Version": "v1"
                }
                params = {
                    "query": query,
                    "per_page": max_images,
                    "orientation": "landscape"
                }
                
                async with session.get(
                    "https://api.unsplash.com/search/photos",
                    headers=headers,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    response.raise_for_status()
                    data = await response.json()
                    
                    results = data.get("results", [])
                    image_urls = []
                    
                    for photo in results[:max_images]:
                        url = photo.get("urls", {}).get("regular")
                        if url:
                            image_urls.append(url)
                    
                    logger.info(f"Unsplash SUCCESS: Found {len(image_urls)} images for '{query}'")
                    return image_urls
                    
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            logger.warning(f"Unsplash API request failed (will retry): {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching from Unsplash: {e}")
            return []
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)),
        reraise=True
    )
    async def _fetch_from_pexels(self, query: str, max_images: int = 3) -> List[str]:
        """Fetch images from Pexels API with retry logic"""
        if not self.pexels_key:
            logger.warning("Pexels API key not configured")
            return []
        
        logger.info(f"FALLBACK: Attempting to fetch images from Pexels for '{query}'")
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": self.pexels_key
                }
                params = {
                    "query": query,
                    "per_page": max_images,
                    "orientation": "landscape"
                }
                
                async with session.get(
                    "https://api.pexels.com/v1/search",
                    headers=headers,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    response.raise_for_status()
                    data = await response.json()
                    
                    photos = data.get("photos", [])
                    image_urls = []
                    
                    for photo in photos[:max_images]:
                        url = photo.get("src", {}).get("large")
                        if url:
                            image_urls.append(url)
                    
                    logger.info(f"Pexels SUCCESS: Found {len(image_urls)} images for '{query}'")
                    return image_urls
                    
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            logger.warning(f"Pexels API request failed (will retry): {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching from Pexels: {e}")
            return []
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)),
        reraise=True
    )
    async def _fetch_from_pixabay(self, query: str, max_images: int = 3) -> List[str]:
        """Fetch images from Pixabay API with retry logic"""
        if not self.pixabay_key:
            logger.warning("Pixabay API key not configured")
            return []
        
        logger.info(f"FALLBACK: Attempting to fetch images from Pixabay for '{query}'")
        
        try:
            async with aiohttp.ClientSession() as session:
                params = {
                    "key": self.pixabay_key,
                    "q": query,
                    "per_page": max_images,
                    "orientation": "horizontal",
                    "image_type": "photo"
                }
                
                async with session.get(
                    "https://pixabay.com/api/",
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    response.raise_for_status()
                    data = await response.json()
                    
                    hits = data.get("hits", [])
                    image_urls = []
                    
                    for hit in hits[:max_images]:
                        url = hit.get("largeImageURL")
                        if url:
                            image_urls.append(url)
                    
                    logger.info(f"Pixabay SUCCESS: Found {len(image_urls)} images for '{query}'")
                    return image_urls
                    
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            logger.warning(f"Pixabay API request failed (will retry): {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching from Pixabay: {e}")
            return []
    
    async def search_images(self, query: str, max_images: int = 3) -> List[str]:
        """
        Search for images with caching and fallback support
        
        Args:
            query: Search query (topic)
            max_images: Maximum number of images to return (default 3)
            
        Returns:
            List of image URLs
        """
        # Check cache first
        cached_images = await self._get_cached_images(query, max_images)
        if cached_images:
            return cached_images
        
        # Try Unsplash first
        try:
            images = await self._fetch_from_unsplash(query, max_images)
            if images:
                await self._cache_images(query, images)
                return images
        except Exception as e:
            logger.error(f"Unsplash failed after retries: {e}")
        
        # Fallback to Pexels
        try:
            images = await self._fetch_from_pexels(query, max_images)
            if images:
                await self._cache_images(query, images)
                return images
        except Exception as e:
            logger.error(f"Pexels failed after retries: {e}")
        
        # Fallback to Pixabay
        try:
            images = await self._fetch_from_pixabay(query, max_images)
            if images:
                await self._cache_images(query, images)
                return images
        except Exception as e:
            logger.error(f"Pixabay failed after retries: {e}")
        
        logger.error(f"All image APIs failed for query '{query}'")
        return []
    
    async def get_random_images(self, count: int = 3) -> List[str]:
        """
        Get random images from Unsplash
        
        Args:
            count: Number of random images to fetch
            
        Returns:
            List of image URLs
        """
        if not self.unsplash_key:
            logger.warning("Unsplash API key not configured")
            return []
        
        logger.info(f"Fetching {count} random images")
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Client-ID {self.unsplash_key}",
                    "Accept-Version": "v1"
                }
                params = {
                    "count": count,
                    "orientation": "landscape"
                }
                
                async with session.get(
                    "https://api.unsplash.com/photos/random",
                    headers=headers,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    response.raise_for_status()
                    photos = await response.json()
                    
                    image_urls = []
                    for photo in photos:
                        url = photo.get("urls", {}).get("regular")
                        if url:
                            image_urls.append(url)
                    
                    logger.info(f"Fetched {len(image_urls)} random images")
                    return image_urls
                    
        except Exception as e:
            logger.error(f"Error fetching random images: {e}")
            return []


# Global instance
image_fetcher = ImageFetcher()
