"""
Tests for image cache database module
"""
import pytest
import os
import time
import sqlite3
from image_cache_db import ImageCacheDB, CACHE_TTL_HOURS


@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary database for testing"""
    db_file = tmp_path / "test_image_cache.db"
    db = ImageCacheDB(str(db_file))
    yield db
    # Cleanup
    if os.path.exists(db_file):
        os.remove(db_file)


def test_db_initialization(temp_db):
    """Test database initialization"""
    # Check that table exists
    conn = sqlite3.connect(temp_db.db_file)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='image_cache'")
    result = cursor.fetchone()
    conn.close()
    
    assert result is not None
    assert result[0] == "image_cache"


def test_cache_image(temp_db):
    """Test caching an image URL"""
    keyword = "test_keyword"
    image_url = "https://example.com/image.jpg"
    
    result = temp_db.cache_image(keyword, image_url)
    
    assert result is True


def test_get_cached_image(temp_db):
    """Test retrieving a cached image"""
    keyword = "test_keyword"
    image_url = "https://example.com/image.jpg"
    
    # Cache the image
    temp_db.cache_image(keyword, image_url)
    
    # Retrieve it
    cached_url = temp_db.get_cached_image(keyword)
    
    assert cached_url == image_url


def test_get_cached_image_not_found(temp_db):
    """Test retrieving a non-existent cached image"""
    cached_url = temp_db.get_cached_image("nonexistent_keyword")
    
    assert cached_url is None


def test_cache_image_lowercase_keyword(temp_db):
    """Test that keywords are stored in lowercase"""
    keyword = "TEST_KEYWORD"
    image_url = "https://example.com/image.jpg"
    
    temp_db.cache_image(keyword, image_url)
    
    # Should be retrievable with lowercase
    cached_url = temp_db.get_cached_image("test_keyword")
    assert cached_url == image_url
    
    # Should be retrievable with original case
    cached_url = temp_db.get_cached_image(keyword)
    assert cached_url == image_url


def test_cache_image_update(temp_db):
    """Test updating an existing cached image"""
    keyword = "test_keyword"
    old_url = "https://example.com/old_image.jpg"
    new_url = "https://example.com/new_image.jpg"
    
    # Cache initial image
    temp_db.cache_image(keyword, old_url)
    
    # Update with new image
    temp_db.cache_image(keyword, new_url)
    
    # Should return the new URL
    cached_url = temp_db.get_cached_image(keyword)
    assert cached_url == new_url


def test_cache_expiration(temp_db):
    """Test that expired cache entries are not returned"""
    keyword = "test_keyword"
    image_url = "https://example.com/image.jpg"
    
    # Manually insert an expired entry
    conn = sqlite3.connect(temp_db.db_file)
    cursor = conn.cursor()
    
    # Set timestamp to more than TTL hours ago
    old_timestamp = int(time.time()) - (CACHE_TTL_HOURS * 3600 + 3600)
    cursor.execute(
        'INSERT INTO image_cache (keyword, image_url, timestamp) VALUES (?, ?, ?)',
        (keyword.lower(), image_url, old_timestamp)
    )
    conn.commit()
    conn.close()
    
    # Should return None for expired entry
    cached_url = temp_db.get_cached_image(keyword)
    assert cached_url is None


def test_clean_expired_cache(temp_db):
    """Test cleaning expired cache entries"""
    # Add a fresh entry
    temp_db.cache_image("fresh_keyword", "https://example.com/fresh.jpg")
    
    # Add an expired entry manually
    conn = sqlite3.connect(temp_db.db_file)
    cursor = conn.cursor()
    old_timestamp = int(time.time()) - (CACHE_TTL_HOURS * 3600 + 3600)
    cursor.execute(
        'INSERT INTO image_cache (keyword, image_url, timestamp) VALUES (?, ?, ?)',
        ("expired_keyword", "https://example.com/expired.jpg", old_timestamp)
    )
    conn.commit()
    conn.close()
    
    # Clean expired entries
    deleted_count = temp_db.clean_expired_cache()
    
    # Should have deleted 1 entry
    assert deleted_count == 1
    
    # Fresh entry should still exist
    assert temp_db.get_cached_image("fresh_keyword") is not None
    
    # Expired entry should be gone
    assert temp_db.get_cached_image("expired_keyword") is None


def test_cache_with_special_characters(temp_db):
    """Test caching with special characters in keyword"""
    keyword = "тест ключевое слово 123!@#"
    image_url = "https://example.com/image.jpg"
    
    result = temp_db.cache_image(keyword, image_url)
    assert result is True
    
    cached_url = temp_db.get_cached_image(keyword)
    assert cached_url == image_url
