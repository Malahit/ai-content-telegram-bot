"""
Image fetching module for the Telegram bot.
Fetches relevant images from Unsplash API based on post topic.
"""
import os
import logging
import requests
from typing import List, Optional

logger = logging.getLogger(__name__)


class ImageFetcher:
    """Fetches images from Unsplash API"""
    
    # Configuration constants
    DEFAULT_TIMEOUT = 10  # seconds
    
    def __init__(self, api_key: Optional[str] = None, timeout: int = DEFAULT_TIMEOUT):
        self.api_key = api_key or os.getenv("UNSPLASH_API_KEY")
        self.base_url = "https://api.unsplash.com"
        self.timeout = timeout
        self.session = requests.Session()
        if self.api_key:
            self.session.headers.update({
                "Authorization": f"Client-ID {self.api_key}",
                "Accept-Version": "v1"
            })
    
    def validate_api_key(self) -> bool:
        """
        Validate Unsplash API key by making a test request
        
        Returns:
            True if API key is valid and validation succeeded (200 OK)
            False if no API key is configured, or if network/server errors occur
            
        Raises:
            RuntimeError: If API key is invalid (401 Unauthorized)
            
        Note:
            Returns False for transient errors to allow bot startup even if
            Unsplash API is temporarily unavailable.
        """
        if not self.api_key:
            logger.warning("Unsplash API key not configured - skipping validation")
            return False
        
        try:
            # Make a test request to validate the API key
            # Using count=1 to minimize response size
            endpoint = f"{self.base_url}/photos/random"
            params = {"count": 1}
            response = self.session.get(endpoint, params=params, timeout=self.timeout)
        except requests.exceptions.RequestException as e:
            # Network/request errors - log and return False (non-fatal)
            logger.error(f"Error validating Unsplash API key: {e}")
            return False
        
        if response.status_code == 200:
            logger.info("Unsplash API key validated successfully")
            return True
        elif response.status_code == 401:
            error_msg = "UNSPLASH_API_KEY is invalid (401 Unauthorized)"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        else:
            logger.warning(f"Unexpected status code during validation: {response.status_code}")
            return False
    
    def search_images(self, query: str, max_images: int = 3) -> List[str]:
        """
        Search for images based on query
        
        Args:
            query: Search query (topic)
            max_images: Maximum number of images to return (default 3)
            
        Returns:
            List of image URLs
        """
        if not self.api_key:
            logger.warning("Unsplash API key not configured")
            return []
        
        try:
            # Search for photos
            endpoint = f"{self.base_url}/search/photos"
            params = {
                "query": query,
                "per_page": max_images,
                "orientation": "landscape"
            }
            
            response = self.session.get(endpoint, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            results = data.get("results", [])
            
            # Extract regular quality image URLs
            image_urls = []
            for photo in results[:max_images]:
                # Use 'regular' size for good quality without being too large
                url = photo.get("urls", {}).get("regular")
                if url:
                    image_urls.append(url)
            
            logger.info(f"Found {len(image_urls)} images for query: {query}")
            return image_urls
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching images from Unsplash: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error in image search: {e}")
            return []
    
    def get_random_images(self, count: int = 3) -> List[str]:
        """
        Get random images
        
        Args:
            count: Number of random images to fetch
            
        Returns:
            List of image URLs
        """
        if not self.api_key:
            logger.warning("Unsplash API key not configured")
            return []
        
        try:
            endpoint = f"{self.base_url}/photos/random"
            params = {
                "count": count,
                "orientation": "landscape"
            }
            
            response = self.session.get(endpoint, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            photos = response.json()
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
