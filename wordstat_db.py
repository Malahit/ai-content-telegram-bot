"""
SQLite database module for Yandex Wordstat cache.
Stores keyword statistics with 24-hour TTL.
"""
import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from contextlib import contextmanager

logger = logging.getLogger(__name__)

DB_FILE = "wordstat_cache.db"
CACHE_TTL_HOURS = 24


class WordstatDB:
    """Manages Wordstat cache in SQLite database"""
    
    def __init__(self, db_file: str = DB_FILE):
        self.db_file = db_file
        self._init_database()
    
    def _init_database(self):
        """Initialize database and create tables if they don't exist"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS wordstat_cache (
                        keyword TEXT PRIMARY KEY,
                        data_json TEXT NOT NULL,
                        timestamp TIMESTAMP NOT NULL
                    )
                """)
                # Create index on timestamp for efficient TTL queries
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_timestamp 
                    ON wordstat_cache(timestamp)
                """)
                conn.commit()
                logger.info("Wordstat database initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise
    
    @contextmanager
    def _get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_file)
        try:
            yield conn
        finally:
            conn.close()
    
    def get(self, keyword: str) -> Optional[Dict[str, Any]]:
        """
        Get cached data for a keyword if it exists and is not expired
        
        Args:
            keyword: The search keyword
            
        Returns:
            Dict with wordstat data or None if not found/expired
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT data_json, timestamp 
                    FROM wordstat_cache 
                    WHERE keyword = ?
                """, (keyword.lower(),))
                
                row = cursor.fetchone()
                if not row:
                    logger.info(f"No cache entry found for keyword: {keyword}")
                    return None
                
                data_json, timestamp_str = row
                timestamp = datetime.fromisoformat(timestamp_str)
                
                # Check if cache entry is expired (older than TTL)
                if datetime.now() - timestamp > timedelta(hours=CACHE_TTL_HOURS):
                    logger.info(f"Cache entry expired for keyword: {keyword}")
                    self.delete(keyword)
                    return None
                
                logger.info(f"Cache hit for keyword: {keyword}")
                return json.loads(data_json)
                
        except Exception as e:
            logger.error(f"Error getting cache entry: {e}")
            return None
    
    def upsert(self, keyword: str, data: Dict[str, Any]) -> bool:
        """
        Insert or update cache entry for a keyword
        
        Args:
            keyword: The search keyword
            data: Dictionary with wordstat data
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO wordstat_cache 
                    (keyword, data_json, timestamp)
                    VALUES (?, ?, ?)
                """, (
                    keyword.lower(),
                    json.dumps(data, ensure_ascii=False),
                    datetime.now().isoformat()
                ))
                conn.commit()
                logger.info(f"Cache entry upserted for keyword: {keyword}")
                return True
        except Exception as e:
            logger.error(f"Error upserting cache entry: {e}")
            return False
    
    def delete(self, keyword: str) -> bool:
        """
        Delete cache entry for a keyword
        
        Args:
            keyword: The search keyword
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM wordstat_cache 
                    WHERE keyword = ?
                """, (keyword.lower(),))
                conn.commit()
                logger.info(f"Cache entry deleted for keyword: {keyword}")
                return True
        except Exception as e:
            logger.error(f"Error deleting cache entry: {e}")
            return False
    
    def cleanup_expired(self) -> int:
        """
        Remove all expired cache entries
        
        Returns:
            Number of entries deleted
        """
        try:
            cutoff_time = datetime.now() - timedelta(hours=CACHE_TTL_HOURS)
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM wordstat_cache 
                    WHERE timestamp < ?
                """, (cutoff_time.isoformat(),))
                deleted_count = cursor.rowcount
                conn.commit()
                logger.info(f"Cleaned up {deleted_count} expired cache entries")
                return deleted_count
        except Exception as e:
            logger.error(f"Error cleaning up expired entries: {e}")
            return 0
    
    def get_all_keywords(self) -> list:
        """
        Get all cached keywords (for debugging/admin purposes)
        
        Returns:
            List of cached keywords
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT keyword FROM wordstat_cache")
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting all keywords: {e}")
            return []


# Global instance
wordstat_db = WordstatDB()
