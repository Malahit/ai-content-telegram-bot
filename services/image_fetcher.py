"""
Image fetcher service for retrieving images from Pexels and Pixabay APIs.
Supports fallback between providers and basic caching.
"""
import aiohttp
import logging
import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)


class ImageFetcher:
    """
    Fetches images from Pexels and Pixabay APIs with fallback support.
    """
    
    def __init__(self, pexels_key: Optional[str] = None, pixabay_key: Optional[str] = None, cache_enabled: bool = True):
        """
        Initialize ImageFetcher with API keys.
        
        Args:
            pexels_key: Pexels API key
            pixabay_key: Pixabay API key
            cache_enabled: Whether to enable caching (currently not implemented)
        """
        self.pexels_key = pexels_key
        self.pixabay_key = pixabay_key
        self.cache_enabled = cache_enabled
        
        self.pexels_url = "https://api.pexels.com/v1/search"
        self.pixabay_url = "https://pixabay.com/api/"
    
    async def fetch_images(self, topic: str, num_images: int = 1) -> List[str]:
        """
        Fetch images for a given topic.
        
        Args:
            topic: Search topic/keyword
            num_images: Number of images to fetch
            
        Returns:
            List of image URLs
        """
        images, _ = await self.search_images(topic, max_images=num_images)
        return images
    
    async def search_images(self, keyword: str, max_images: int = 3) -> Tuple[List[str], Optional[str]]:
        """
        Search for images using available APIs with fallback.
        
        Args:
            keyword: Search keyword
            max_images: Maximum number of images to return
            
        Returns:
            Tuple of (list of image URLs, error message if any)
        """
        # Try Pexels first
        if self.pexels_key:
            try:
                images = await self._fetch_from_pexels(keyword, max_images)
                if images:
                    logger.info(f"✅ Fetched {len(images)} images from Pexels for '{keyword}'")
                    return images, None
            except Exception as e:
                logger.warning(f"Pexels API failed for '{keyword}': {e}")
        
        # Fallback to Pixabay
        if self.pixabay_key:
            try:
                images = await self._fetch_from_pixabay(keyword, max_images)
                if images:
                    logger.info(f"✅ Fetched {len(images)} images from Pixabay for '{keyword}'")
                    return images, None
            except Exception as e:
                logger.warning(f"Pixabay API failed for '{keyword}': {e}")
        
        # No API keys configured or all failed
        if not self.pexels_key and not self.pixabay_key:
            error_msg = "Image API keys not configured"
            logger.error(error_msg)
            return [], error_msg
        
        error_msg = "No results found or all APIs failed"
        logger.warning(f"⚠️ {error_msg} for '{keyword}'")
        return [], error_msg
    
    async def _fetch_from_pexels(self, keyword: str, max_images: int) -> List[str]:
        """
        Fetch images from Pexels API.
        
        Args:
            keyword: Search keyword
            max_images: Maximum number of images
            
        Returns:
            List of image URLs
        """
        headers = {"Authorization": self.pexels_key}
        params = {
            "query": keyword,
            "per_page": max_images,
            "orientation": "landscape"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(self.pexels_url, headers=headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    photos = data.get("photos", [])
                    return [photo["src"]["large"] for photo in photos[:max_images]]
                elif response.status == 401:
                    raise ValueError("Invalid Pexels API key")
                else:
                    raise Exception(f"Pexels API returned status {response.status}")
    
    async def _fetch_from_pixabay(self, keyword: str, max_images: int) -> List[str]:
        """
        Fetch images from Pixabay API.
        
        Args:
            keyword: Search keyword
            max_images: Maximum number of images
            
        Returns:
            List of image URLs
        """
        params = {
            "key": self.pixabay_key,
            "q": keyword,
            "per_page": max_images,
            "image_type": "photo",
            "orientation": "horizontal"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(self.pixabay_url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    hits = data.get("hits", [])
                    return [hit["largeImageURL"] for hit in hits[:max_images]]
                elif response.status == 401:
                    raise ValueError("Invalid Pixabay API key")
                else:
                    raise Exception(f"Pixabay API returned status {response.status}")


class ImageCache:
    """Simple image cache with SQLite backend"""
    
    def __init__(self, db_path: str = "image_cache.db", ttl_hours: int = 48):
        self.db_path = db_path
        self.ttl_hours = ttl_hours
        self._init_db()
    
    def _init_db(self):
        """Initialize SQLite database for caching"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS image_cache (
                keyword TEXT PRIMARY KEY,
                image_urls TEXT,
                cached_at TEXT
            )
        """)
        conn.commit()
        conn.close()
    
    def cache_images(self, keyword: str, image_urls: List[str]):
        """Cache images for a keyword"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        urls_json = json.dumps(image_urls)
        cached_at = datetime.now().isoformat()
        
        cursor.execute("""
            INSERT OR REPLACE INTO image_cache (keyword, image_urls, cached_at)
            VALUES (?, ?, ?)
        """, (keyword, urls_json, cached_at))
        
        conn.commit()
        conn.close()
    
    def get_cached_images(self, keyword: str) -> Optional[List[str]]:
        """Get cached images for a keyword"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT image_urls, cached_at FROM image_cache WHERE keyword = ?
        """, (keyword,))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return None
        
        urls_json, cached_at_str = result
        cached_at = datetime.fromisoformat(cached_at_str)
        
        # Check if cache is still valid
        if datetime.now() - cached_at > timedelta(hours=self.ttl_hours):
            return None
        
        return json.loads(urls_json)
