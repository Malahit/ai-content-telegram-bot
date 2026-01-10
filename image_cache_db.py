"""
SQLite-based image cache for the Telegram bot.
Caches image URLs with 48-hour TTL to reduce API calls.
"""
import sqlite3
import logging
import time
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)

DB_FILE = "image_cache.db"
CACHE_TTL_HOURS = 48


class ImageCacheDB:
    """Manages SQLite cache for image URLs"""
    
    def __init__(self, db_file: str = DB_FILE):
        self.db_file = db_file
        self._init_db()
    
    def _init_db(self):
        """Initialize database and create tables if they don't exist"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS image_cache (
                    keyword TEXT PRIMARY KEY,
                    image_url TEXT NOT NULL,
                    timestamp INTEGER NOT NULL
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info(f"Image cache database initialized: {self.db_file}")
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
    
    def cache_image(self, keyword: str, image_url: str) -> bool:
        """
        Save image URL to cache
        
        Args:
            keyword: Search keyword
            image_url: URL of the image
            
        Returns:
            True if successful, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            timestamp = int(time.time())
            
            # Insert or replace existing entry
            cursor.execute('''
                INSERT OR REPLACE INTO image_cache (keyword, image_url, timestamp)
                VALUES (?, ?, ?)
            ''', (keyword.lower(), image_url, timestamp))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Cached image for keyword: {keyword}")
            return True
        except Exception as e:
            logger.error(f"Error caching image: {e}")
            return False
    
    def get_cached_image(self, keyword: str) -> Optional[str]:
        """
        Retrieve image URL from cache if not expired
        
        Args:
            keyword: Search keyword
            
        Returns:
            Image URL if found and not expired, None otherwise
        """
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT image_url, timestamp FROM image_cache
                WHERE keyword = ?
            ''', (keyword.lower(),))
            
            result = cursor.fetchone()
            conn.close()
            
            if not result:
                logger.debug(f"No cached image found for keyword: {keyword}")
                return None
            
            image_url, timestamp = result
            
            # Check if cache is still valid (within TTL)
            current_time = int(time.time())
            age_hours = (current_time - timestamp) / 3600
            
            if age_hours > CACHE_TTL_HOURS:
                logger.info(f"Cached image expired for keyword: {keyword} (age: {age_hours:.1f}h)")
                self._delete_cached_image(keyword)
                return None
            
            logger.info(f"Retrieved cached image for keyword: {keyword} (age: {age_hours:.1f}h)")
            return image_url
            
        except Exception as e:
            logger.error(f"Error retrieving cached image: {e}")
            return None
    
    def _delete_cached_image(self, keyword: str) -> bool:
        """
        Delete cached image entry
        
        Args:
            keyword: Search keyword
            
        Returns:
            True if successful, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM image_cache WHERE keyword = ?', (keyword.lower(),))
            
            conn.commit()
            conn.close()
            
            return True
        except Exception as e:
            logger.error(f"Error deleting cached image: {e}")
            return False
    
    def clean_expired_cache(self) -> int:
        """
        Remove all expired cache entries
        
        Returns:
            Number of entries removed
        """
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cutoff_time = int(time.time()) - (CACHE_TTL_HOURS * 3600)
            
            cursor.execute('DELETE FROM image_cache WHERE timestamp < ?', (cutoff_time,))
            
            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()
            
            logger.info(f"Cleaned {deleted_count} expired cache entries")
            return deleted_count
        except Exception as e:
            logger.error(f"Error cleaning expired cache: {e}")
            return 0


# Global instance
image_cache = ImageCacheDB()
