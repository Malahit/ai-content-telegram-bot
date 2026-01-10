"""
Image fetching module for the Telegram bot.
Fetches relevant images from Unsplash API based on post topic.
Includes retry logic, fallback to Pexels/Pixabay, and SQLite caching.
"""
import os
import logging
import asyncio
from typing import List, Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import aiohttp
import time

from image_cache_db import image_cache

logger = logging.getLogger(__name__)


class RateLimiter:
    """Simple rate limiter for API calls"""
    
    def __init__(self, max_calls: int = 5, period: int = 60):
        """
        Args:
            max_calls: Maximum number of calls allowed
            period: Time period in seconds
        """
        self.max_calls = max_calls
        self.period = period
        self.calls = []
    
    async def wait_if_needed(self):
        """Wait if rate limit would be exceeded"""
        now = time.time()
        # Remove calls older than the period
        self.calls = [call_time for call_time in self.calls if now - call_time < self.period]
        
        if len(self.calls) >= self.max_calls:
            # Calculate wait time
            oldest_call = min(self.calls)
            wait_time = self.period - (now - oldest_call)
            if wait_time > 0:
                logger.info(f"Rate limit reached, waiting {wait_time:.1f}s")
                await asyncio.sleep(wait_time)
                self.calls = []
        
        self.calls.append(time.time())


class ImageFetcher:
    """Fetches images from Unsplash, Pexels, and Pixabay APIs with caching"""
    
    # Configuration constants
    DEFAULT_TIMEOUT = 10  # seconds
    USER_AGENT = "AI-Content-Telegram-Bot/2.2 (https://github.com/Malahit/ai-content-telegram-bot)"
    
    def __init__(self, unsplash_key: Optional[str] = None, 
                 pexels_key: Optional[str] = None,
                 pixabay_key: Optional[str] = None,
                 timeout: int = DEFAULT_TIMEOUT):
        self.unsplash_key = unsplash_key or os.getenv("UNSPLASH_API_KEY")
        self.pexels_key = pexels_key or os.getenv("PEXELS_API_KEY")
        self.pixabay_key = pixabay_key or os.getenv("PIXABAY_API_KEY")
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.rate_limiter = RateLimiter(max_calls=5, period=60)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError))
    )
    async def _fetch_from_unsplash(self, query: str, max_images: int = 3) -> List[str]:
        """
        Fetch images from Unsplash API with retry logic
        
        Args:
            query: Search query
            max_images: Maximum number of images to return
            
        Returns:
            List of image URLs
        """
        if not self.unsplash_key:
            logger.warning("Unsplash API key not configured")
            return []
        
        await self.rate_limiter.wait_if_needed()
        
        headers = {
            "Authorization": f"Client-ID {self.unsplash_key}",
            "Accept-Version": "v1",
            "User-Agent": self.USER_AGENT
        }
        
        params = {
            "query": query,
            "per_page": max_images,
            "orientation": "landscape"
        }
        
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.get(
                "https://api.unsplash.com/search/photos",
                headers=headers,
                params=params
            ) as response:
                # Handle rate limiting
                if response.status == 429:
                    logger.warning("Unsplash rate limit exceeded")
                    raise aiohttp.ClientError("Rate limit exceeded")
                
                # Handle forbidden
                if response.status == 403:
                    logger.error("Unsplash API access forbidden - check API key")
                    raise aiohttp.ClientError("Access forbidden")
                
                response.raise_for_status()
                data = await response.json()
                
                results = data.get("results", [])
                image_urls = [
                    photo.get("urls", {}).get("regular")
                    for photo in results[:max_images]
                    if photo.get("urls", {}).get("regular")
                ]
                
                logger.info(f"Unsplash: Found {len(image_urls)} images for query: {query}")
                return image_urls
    
    async def _fetch_from_pexels(self, query: str, max_images: int = 3) -> List[str]:
        """
        Fetch images from Pexels API as fallback
        
        Args:
            query: Search query
            max_images: Maximum number of images to return
            
        Returns:
            List of image URLs
        """
        if not self.pexels_key:
            logger.debug("Pexels API key not configured")
            return []
        
        headers = {
            "Authorization": self.pexels_key,
            "User-Agent": self.USER_AGENT
        }
        
        params = {
            "query": query,
            "per_page": max_images,
            "orientation": "landscape"
        }
        
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(
                    "https://api.pexels.com/v1/search",
                    headers=headers,
                    params=params
                ) as response:
                    if response.status != 200:
                        logger.warning(f"Pexels API returned status {response.status}")
                        return []
                    
                    data = await response.json()
                    photos = data.get("photos", [])
                    
                    image_urls = [
                        photo.get("src", {}).get("large")
                        for photo in photos[:max_images]
                        if photo.get("src", {}).get("large")
                    ]
                    
                    logger.info(f"Pexels: Found {len(image_urls)} images for query: {query}")
                    return image_urls
        except Exception as e:
            logger.error(f"Error fetching from Pexels: {e}")
            return []
    
    async def _fetch_from_pixabay(self, query: str, max_images: int = 3) -> List[str]:
        """
        Fetch images from Pixabay API as fallback
        
        Args:
            query: Search query
            max_images: Maximum number of images to return
            
        Returns:
            List of image URLs
        """
        if not self.pixabay_key:
            logger.debug("Pixabay API key not configured")
            return []
        
        params = {
            "key": self.pixabay_key,
            "q": query,
            "per_page": max_images,
            "orientation": "horizontal",
            "image_type": "photo"
        }
        
        headers = {
            "User-Agent": self.USER_AGENT
        }
        
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(
                    "https://pixabay.com/api/",
                    headers=headers,
                    params=params
                ) as response:
                    if response.status != 200:
                        logger.warning(f"Pixabay API returned status {response.status}")
                        return []
                    
                    data = await response.json()
                    hits = data.get("hits", [])
                    
                    image_urls = [
                        hit.get("largeImageURL")
                        for hit in hits[:max_images]
                        if hit.get("largeImageURL")
                    ]
                    
                    logger.info(f"Pixabay: Found {len(image_urls)} images for query: {query}")
                    return image_urls
        except Exception as e:
            logger.error(f"Error fetching from Pixabay: {e}")
            return []
    
    async def fetch_image(self, query: str) -> Optional[str]:
        """
        Fetch a single image with caching and fallback
        
        Args:
            query: Search query
            
        Returns:
            Image URL or None
        """
        # Check cache first
        cached_url = image_cache.get_cached_image(query)
        if cached_url:
            return cached_url
        
        # Try Unsplash first
        try:
            urls = await self._fetch_from_unsplash(query, max_images=1)
            if urls:
                image_cache.cache_image(query, urls[0])
                return urls[0]
        except Exception as e:
            logger.warning(f"Unsplash failed: {e}, trying fallback")
        
        # Fallback to Pexels
        urls = await self._fetch_from_pexels(query, max_images=1)
        if urls:
            image_cache.cache_image(query, urls[0])
            return urls[0]
        
        # Fallback to Pixabay
        urls = await self._fetch_from_pixabay(query, max_images=1)
        if urls:
            image_cache.cache_image(query, urls[0])
            return urls[0]
        
        logger.error(f"All image sources failed for query: {query}")
        return None
    
    async def search_images(self, query: str, max_images: int = 3) -> List[str]:
        """
        Search for images based on query with caching and fallback
        
        Args:
            query: Search query (topic)
            max_images: Maximum number of images to return (default 3)
            
        Returns:
            List of image URLs
        """
        # Try Unsplash first
        try:
            urls = await self._fetch_from_unsplash(query, max_images)
            if urls:
                # Cache the first image for single-image requests
                if urls:
                    image_cache.cache_image(query, urls[0])
                return urls
        except Exception as e:
            logger.warning(f"Unsplash failed: {e}, trying fallback")
        
        # Fallback to Pexels
        urls = await self._fetch_from_pexels(query, max_images)
        if urls:
            if urls:
                image_cache.cache_image(query, urls[0])
            return urls
        
        # Fallback to Pixabay
        urls = await self._fetch_from_pixabay(query, max_images)
        if urls:
            if urls:
                image_cache.cache_image(query, urls[0])
            return urls
        
        logger.error(f"All image sources failed for query: {query}")
        return []


# Global instance
image_fetcher = ImageFetcher()

