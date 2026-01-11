#!/usr/bin/env python3
"""
Simple test script to verify Pexels API integration.
This script tests the image_fetcher module with sample queries.
"""
import os
import logging
from dotenv import load_dotenv
from image_fetcher import ImageFetcher

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_pexels_api():
    """Test Pexels API integration"""
    load_dotenv()
    
    api_key = os.getenv("PEXELS_API_KEY")
    
    if not api_key:
        logger.error("❌ PEXELS_API_KEY not found in environment variables!")
        logger.info("Please add PEXELS_API_KEY to your .env file")
        return False
    
    logger.info(f"✅ PEXELS_API_KEY found (length: {len(api_key)})")
    
    # Create ImageFetcher instance
    fetcher = ImageFetcher(api_key=api_key)
    
    # Test 1: Search for specific topic
    logger.info("\n=== Test 1: Search for 'fitness' ===")
    results = fetcher.search_images("fitness", max_images=3)
    
    if results:
        logger.info(f"✅ Found {len(results)} images for 'fitness'")
        for i, url in enumerate(results, 1):
            logger.info(f"  {i}. {url}")
    else:
        logger.error("❌ No images found for 'fitness'")
        return False
    
    # Test 2: Search for another topic
    logger.info("\n=== Test 2: Search for 'business' ===")
    results = fetcher.search_images("business", max_images=2)
    
    if results:
        logger.info(f"✅ Found {len(results)} images for 'business'")
        for i, url in enumerate(results, 1):
            logger.info(f"  {i}. {url}")
    else:
        logger.error("❌ No images found for 'business'")
        return False
    
    # Test 3: Get random curated images
    logger.info("\n=== Test 3: Get random curated images ===")
    results = fetcher.get_random_images(count=2)
    
    if results:
        logger.info(f"✅ Found {len(results)} random images")
        for i, url in enumerate(results, 1):
            logger.info(f"  {i}. {url}")
    else:
        logger.error("❌ No random images found")
        return False
    
    logger.info("\n✅ All tests passed!")
    return True

if __name__ == "__main__":
    success = test_pexels_api()
    exit(0 if success else 1)
