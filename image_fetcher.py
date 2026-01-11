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
    """Fetches images from Pexels API"""
    
    # Configuration constants
    DEFAULT_TIMEOUT = 10  # seconds
    
    def __init__(self, api_key: Optional[str] = None, timeout: int = DEFAULT_TIMEOUT):
        self.api_key = api_key or os.getenv("PEXELS_API_KEY")
        self.base_url = "https://api.pexels.com/v1"
        self.timeout = timeout
        self.session = requests.Session()
        if self.api_key:
            self.session.headers.update({
                "Authorization": self.api_key
            })
    
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
            # Search for photos on Pexels
            endpoint = f"{self.base_url}/search"
            params = {
                "query": query,
                "per_page": max_images,
                "orientation": "landscape"
            }
            
            logger.info(f"Searching Pexels for '{query}' with params: {params}")
            response = self.session.get(endpoint, params=params, timeout=self.timeout)
            
            # Log response details for debugging
            logger.info(f"Pexels API response status: {response.status_code}")
            
            response.raise_for_status()
            
            data = response.json()
            photos = data.get("photos", [])
            
            # Extract image URLs (use 'large' size for good quality)
            image_urls = []
            for photo in photos[:max_images]:
                # Pexels provides src object with different sizes
                url = photo.get("src", {}).get("large")
                if url:
                    image_urls.append(url)
                    logger.debug(f"Added image URL: {url}")
            
            logger.info(f"Successfully found {len(image_urls)} images for query: {query}")
            return image_urls
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error fetching images from Pexels: {e} (Status: {e.response.status_code if e.response else 'N/A'})")
            if e.response:
                logger.error(f"Response content: {e.response.text[:200]}")
            return []
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error fetching images from Pexels: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error in image search: {e}")
            return []
    
    def get_random_images(self, count: int = 3) -> List[str]:
        """
        Get random curated images
        
        Args:
            count: Number of random images to fetch
            
        Returns:
            List of image URLs
        """
        if not self.api_key:
            logger.warning("Pexels API key not configured")
            return []
        
        try:
            # Get curated photos from Pexels
            endpoint = f"{self.base_url}/curated"
            params = {
                "per_page": count
            }
            
            logger.info(f"Fetching {count} curated images from Pexels")
            response = self.session.get(endpoint, params=params, timeout=self.timeout)
            
            # Log response details for debugging
            logger.info(f"Pexels API response status: {response.status_code}")
            
            response.raise_for_status()
            
            data = response.json()
            photos = data.get("photos", [])
            image_urls = []
            
            for photo in photos[:count]:
                url = photo.get("src", {}).get("large")
                if url:
                    image_urls.append(url)
                    logger.debug(f"Added random image URL: {url}")
            
            logger.info(f"Successfully fetched {len(image_urls)} random images")
            return image_urls
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error fetching random images from Pexels: {e} (Status: {e.response.status_code if e.response else 'N/A'})")
            if e.response:
                logger.error(f"Response content: {e.response.text[:200]}")
            return []
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error fetching random images from Pexels: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching random images: {e}")
            return []


# Global instance
image_fetcher = ImageFetcher()
