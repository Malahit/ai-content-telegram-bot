#!/usr/bin/env python3
"""
Unit tests for database module (image caching).
"""
import os
import sys
import tempfile
import time

# Add parent directory to path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database import ImageDatabase


# Test constants
TEST_TTL_HOURS = 0.001  # ~3.6 seconds for quick testing


def test_database_initialization():
    """Test database initialization"""
    print("\n🧪 Test 1: Database Initialization")
    
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name
    
    try:
        db = ImageDatabase(db_path=db_path, ttl_hours=24)
        assert os.path.exists(db_path), "Database file should be created"
        print("✅ Database initialized successfully")
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)


def test_cache_storage_and_retrieval():
    """Test caching and retrieving images"""
    print("\n🧪 Test 2: Cache Storage and Retrieval")
    
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name
    
    try:
        db = ImageDatabase(db_path=db_path, ttl_hours=24)
        
        # Cache an image
        prompt = "test prompt"
        image_url = "https://example.com/image.jpg"
        db.cache_image(prompt, image_url)
        
        # Retrieve it
        cached_url = db.get_cached_image(prompt)
        assert cached_url == image_url, f"Expected {image_url}, got {cached_url}"
        print("✅ Image cached and retrieved successfully")
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)


def test_cache_expiration():
    """Test cache expiration"""
    print("\n🧪 Test 3: Cache Expiration")
    
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name
    
    try:
        # Use very short TTL for testing
        db = ImageDatabase(db_path=db_path, ttl_hours=TEST_TTL_HOURS)
        
        prompt = "test prompt"
        image_url = "https://example.com/image.jpg"
        db.cache_image(prompt, image_url)
        
        # Should be cached immediately (check within first 0.1 seconds)
        time.sleep(0.1)
        cached_url = db.get_cached_image(prompt)
        assert cached_url == image_url, "Image should be cached immediately after insertion"
        
        # Wait for expiration (TTL is 3.6 seconds, wait 4 seconds to be sure)
        time.sleep(4)
        
        # Should be expired now
        cached_url = db.get_cached_image(prompt)
        assert cached_url is None, "Image should be expired"
        print("✅ Cache expiration works correctly")
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)


def test_cleanup_expired():
    """Test cleanup of expired entries"""
    print("\n🧪 Test 4: Cleanup Expired Entries")
    
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name
    
    try:
        db = ImageDatabase(db_path=db_path, ttl_hours=TEST_TTL_HOURS)
        
        # Cache multiple images
        for i in range(3):
            db.cache_image(f"prompt_{i}", f"https://example.com/image_{i}.jpg")
        
        # Wait for expiration (TTL is 3.6 seconds, wait 4 seconds)
        time.sleep(4)
        
        # Cleanup
        deleted_count = db.cleanup_expired()
        assert deleted_count == 3, f"Expected 3 deleted, got {deleted_count}"
        print("✅ Expired entries cleaned up successfully")
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)


if __name__ == '__main__':
    print("Running Database module tests...")
    
    try:
        test_database_initialization()
        test_cache_storage_and_retrieval()
        test_cache_expiration()
        test_cleanup_expired()
        print("\n✅ All database tests passed!")
        sys.exit(0)
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
