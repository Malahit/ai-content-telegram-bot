"""
Database module for AI Content Telegram Bot.

Manages SQLite database for caching AI-generated images with TTL.
"""

import sqlite3
import time
from typing import Optional
from logger_config import logger


class ImageDatabase:
    """
    SQLite database manager for caching AI-generated images.
    
    Stores image URLs with a 24-hour TTL to reduce API calls and improve performance.
    """
    
    def __init__(self, db_path: str = "cache_images.db", ttl_hours: int = 24):
        """
        Initialize database connection and schema.
        
        Args:
            db_path: Path to SQLite database file
            ttl_hours: Time-to-live for cached images in hours (default: 24)
        """
        self.db_path = db_path
        self.ttl_seconds = ttl_hours * 3600
        self._init_db()
        logger.info(f"Image cache database initialized: {db_path} (TTL: {ttl_hours}h)")
    
    def _init_db(self):
        """Initialize database schema with cache_images table."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache_images (
                    prompt TEXT PRIMARY KEY,
                    image_url TEXT NOT NULL,
                    timestamp INTEGER NOT NULL,
                    model TEXT DEFAULT 'flux.1-schnell'
                )
            """)
            conn.commit()
            logger.debug("cache_images table initialized")
    
    def get_cached_image(self, prompt: str) -> Optional[str]:
        """
        Retrieve cached image URL for a prompt if not expired.
        
        Args:
            prompt: The image generation prompt
            
        Returns:
            Image URL if cached and valid, None otherwise
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT image_url, timestamp FROM cache_images WHERE prompt = ?",
                (prompt.lower().strip(),)
            )
            row = cursor.fetchone()
            
            if row:
                image_url, timestamp = row
                # Check if cache is still valid
                if time.time() - timestamp < self.ttl_seconds:
                    logger.info(f"Cache HIT for prompt: '{prompt[:50]}...'")
                    return image_url
                else:
                    # Clean up expired entry
                    conn.execute("DELETE FROM cache_images WHERE prompt = ?", (prompt.lower().strip(),))
                    conn.commit()
                    logger.info(f"Cache EXPIRED for prompt: '{prompt[:50]}...'")
            
            logger.debug(f"Cache MISS for prompt: '{prompt[:50]}...'")
            return None
    
    def cache_image(self, prompt: str, image_url: str, model: str = 'flux.1-schnell'):
        """
        Cache an image URL for a prompt.
        
        Args:
            prompt: The image generation prompt
            image_url: URL of the generated image
            model: Model used for generation (default: 'flux.1-schnell')
        """
        if not image_url:
            return
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO cache_images (prompt, image_url, timestamp, model) VALUES (?, ?, ?, ?)",
                (prompt.lower().strip(), image_url, int(time.time()), model)
            )
            conn.commit()
            logger.info(f"Cached image for prompt: '{prompt[:50]}...' -> {image_url}")
    
    def cleanup_expired(self):
        """Remove all expired cache entries."""
        with sqlite3.connect(self.db_path) as conn:
            cutoff_time = int(time.time()) - self.ttl_seconds
            cursor = conn.execute("DELETE FROM cache_images WHERE timestamp < ?", (cutoff_time,))
            deleted_count = cursor.rowcount
            conn.commit()
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} expired image cache entries")
            return deleted_count


# Global database instance
image_db = ImageDatabase()
