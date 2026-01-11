"""
Image fetching module for the Telegram bot.
Fetches relevant images from Pexels API based on post topic.
"""
import os
import logging
import requests
from typing import List, Optional

logger = logging.getLogger(__name__)


class ImageFetcher:
    """
    Fetches images from Pexels API
    
    Note: Pexels API expects the API key directly in the Authorization header
    (not as a Bearer token). Simply pass your API key as-is.
    """
    
    # Configuration constants
    DEFAULT_TIMEOUT = 10  # seconds
    
    def __init__(self, api_key: Optional[str] = None, timeout: int = DEFAULT_TIMEOUT, validate: bool = False):
        self.api_key = api_key or os.getenv("PEXELS_API_KEY")
        self.base_url = "https://api.pexels.com/v1"
        self.timeout = timeout
        self.session = requests.Session()
        self.validated = False
        
        if self.api_key:
            self.session.headers.update({
                "Authorization": self.api_key
            })
            # Optionally validate API key on initialization
            if validate:
                self.validated = self._validate_api_key()
    
    def _validate_api_key(self) -> bool:
        """
        Validate Pexels API key by making a test request
        
        Returns:
            True if API key is valid, False otherwise
        """
        try:
            endpoint = f"{self.base_url}/search"
            params = {
                "query": "nature",
                "per_page": 1
            }
            response = self.session.get(endpoint, params=params, timeout=self.timeout)
            
            if response.status_code == 401:
                logger.error("Pexels API key is invalid or unauthorized")
                return False
            
            response.raise_for_status()
            logger.info("Pexels API key validated successfully")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error validating Pexels API key: {e}")
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
            logger.warning("Pexels API key not configured")
            return []
        
        try:
            # Search for photos
            endpoint = f"{self.base_url}/search"
            params = {
                "query": query,
                "per_page": max_images,
                "orientation": "landscape"
            }
            
            response = self.session.get(endpoint, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            photos = data.get("photos", [])
            
            # Extract image URLs
            image_urls = []
            for photo in photos[:max_images]:
                # Use 'large' size for good quality
                url = photo.get("src", {}).get("large")
                if url:
                    image_urls.append(url)
            
            logger.info(f"Found {len(image_urls)} images for query: {query}")
            return image_urls
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching images from Pexels: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error in image search: {e}")
            return []
    
    def get_random_images(self, count: int = 3) -> List[str]:
        """
        Get random images (curated photos from Pexels)
        
        Args:
            count: Number of random images to fetch
            
        Returns:
            List of image URLs
        """
        if not self.api_key:
            logger.warning("Pexels API key not configured")
            return []
        
        try:
            endpoint = f"{self.base_url}/curated"
            params = {
                "per_page": count
            }
            
            response = self.session.get(endpoint, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            photos = data.get("photos", [])
            image_urls = []
            
            for photo in photos[:count]:
                url = photo.get("src", {}).get("large")
                if url:
                    image_urls.append(url)
            
            logger.info(f"Fetched {len(image_urls)} random images")
            return image_urls
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching random images: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error in get_random_images: {e}")
            return []


# Global instance (validation disabled to avoid import-time network calls)
image_fetcher = ImageFetcher(validate=False)
