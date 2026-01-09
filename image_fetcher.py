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
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("UNSPLASH_API_KEY")
        self.base_url = "https://api.unsplash.com"
        self.session = requests.Session()
        if self.api_key:
            self.session.headers.update({
                "Authorization": f"Client-ID {self.api_key}",
                "Accept-Version": "v1"
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
            
            response = self.session.get(endpoint, params=params, timeout=10)
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
            
            response = self.session.get(endpoint, params=params, timeout=10)
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
