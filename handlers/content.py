"""
Content generation handler for AI Content Telegram Bot.

This module handles the image generation flow using Perplexity API with Pexels/Pixabay fallback.
"""

from typing import Optional, Tuple
from logger_config import logger
from utils.perplexity import generate_image as perplexity_generate_image, PerplexityError
from database import image_db


async def generate_content_with_image(topic: str, image_fetcher=None) -> Tuple[Optional[str], Optional[str]]:
    """
    Generate image for a given topic using Perplexity API.
    
    Note: Text content generation is handled separately by the caller via api_client.
    This function only handles image generation with caching and fallback.
    
    Priority chain for images:
    1. Check cache (24h TTL)
    2. Try Perplexity AI image generation
    3. Fallback to Pexels search
    4. Return None if all methods fail
    
    Args:
        topic: The topic for image generation
        image_fetcher: Optional ImageFetcher instance for Pexels fallback
        
    Returns:
        Tuple of (image_url, error_message)
        - image_url: URL of the generated/fetched image, or None if failed
        - error_message: Error description if image generation failed, or None if successful
    """
    logger.info(f"Starting content+image generation pipeline for topic: {topic}")
    
    # Generate image with Perplexity (with caching and fallback)
    image_url = await generate_perplexity_image_with_fallback(topic, image_fetcher)
    
    if image_url:
        logger.info(f"✅ Content generation pipeline successful for '{topic}'")
        return image_url, None
    else:
        error_msg = "Не удалось сгенерировать изображение (Perplexity и Pexels недоступны)"
        logger.warning(f"Content generation pipeline completed with no image for '{topic}'")
        return None, error_msg


async def generate_perplexity_image_with_fallback(topic: str, image_fetcher=None) -> Optional[str]:
    """
    Generate an image using Perplexity with Pexels fallback and caching.
    
    Priority chain:
    1. Check cache (24h TTL)
    2. Try Perplexity image generation with optimized prompts
    3. Fallback to Pexels/Pixabay
    4. Return None if all methods fail
    
    Args:
        topic: The topic/prompt for image generation
        image_fetcher: Optional ImageFetcher instance for fallback
        
    Returns:
        Image URL or None if generation failed
    """
    logger.info(f"Generating image for topic: {topic}")
    
    # Create topic-specific, high-quality prompt in Russian for better results
    # Format: "профессиональное фото на тему {topic}, реалистичная фотосъёмка, высокая детализация, качество 4K, realistic photography"
    image_prompt = f"профессиональное фото на тему {topic}, реалистичная фотосъёмка, высокая детализация, качество 4K, realistic photography"
    
    # Check cache first using the full image prompt as key for consistency
    cached_url = image_db.get_cached_image(image_prompt)
    if cached_url:
        logger.info(f"Using cached Perplexity image for '{topic}'")
        return cached_url
    
    # Try Perplexity image generation
    try:
        image_url = await perplexity_generate_image(image_prompt)
        
        if image_url:
            # Cache the generated image using the same prompt key
            image_db.cache_image(image_prompt, image_url)
            logger.info(f"✅ Perplexity image generated and cached: {image_url}")
            return image_url
        else:
            logger.warning(f"Perplexity returned no image for '{topic}'")
    except PerplexityError as e:
        logger.warning(f"Perplexity image generation failed for '{topic}': {e}")
    except Exception as e:
        logger.error(f"Unexpected error in Perplexity image generation for '{topic}': {e}", exc_info=True)
    
    # Fallback to Pexels if Perplexity fails and image_fetcher is available
    if image_fetcher:
        logger.info(f"Falling back to Pexels for '{topic}'")
        try:
            image_urls, error_msg = await image_fetcher.search_images(topic, max_images=1)
            if image_urls:
                logger.info(f"✅ Pexels fallback successful: {image_urls[0]}")
                return image_urls[0]
            else:
                logger.warning(f"Pexels fallback also failed for '{topic}': {error_msg}")
        except Exception as e:
            logger.error(f"Pexels fallback error for '{topic}': {e}", exc_info=True)
    
    logger.error(f"All image generation methods failed for '{topic}'")
    return None
