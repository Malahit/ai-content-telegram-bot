"""
Perplexity API utilities for image and text generation.

This module provides async functions for interacting with Perplexity's Sonar Pro API
for both text and image generation.
"""

import aiohttp
import asyncio
from typing import Optional, Dict, Any
from logger_config import logger
from config import config


# Constants
MAX_PROMPT_LOG_LENGTH = 50


class PerplexityError(Exception):
    """Custom exception for Perplexity API errors."""
    pass


def _truncate_prompt(prompt: str) -> str:
    """
    Truncate prompt for logging purposes.
    
    Args:
        prompt: The prompt to truncate
        
    Returns:
        Truncated prompt string
    """
    if len(prompt) > MAX_PROMPT_LOG_LENGTH:
        return f"{prompt[:MAX_PROMPT_LOG_LENGTH]}..."
    return prompt


async def generate_image(prompt: str, model: str = 'flux.1-schnell') -> Optional[str]:
    """
    Generate an image using Perplexity's image generation API.
    
    Args:
        prompt: The text prompt describing the image to generate
        model: The model to use (default: 'flux.1-schnell')
        
    Returns:
        str: URL of the generated image, or None if generation failed
        
    Raises:
        PerplexityError: If API request fails after retries
    """
    logger.info(f"Generating image with Perplexity: prompt='{_truncate_prompt(prompt)}', model='{model}'")
    
    url = "https://api.perplexity.ai/images/generate"
    headers = {
        "Authorization": f"Bearer {config.pplx_api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": model,
        "prompt": prompt
    }
    
    max_retries = 3
    timeout = aiohttp.ClientTimeout(total=config.api_timeout)
    
    for attempt in range(1, max_retries + 1):
        try:
            logger.debug(f"Perplexity image API request attempt {attempt}/{max_retries}")
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, headers=headers, json=data) as response:
                    status = response.status
                    logger.debug(f"Perplexity image API response: status={status}")
                    
                    if status == 401:
                        logger.error("Perplexity API: Invalid API key (401 Unauthorized)")
                        raise PerplexityError("Invalid Perplexity API key")
                    
                    if status == 429:
                        logger.warning(f"Perplexity API: Rate limit exceeded (429 Too Many Requests)")
                        if attempt < max_retries:
                            await asyncio.sleep(2 ** attempt)  # Exponential backoff
                            continue
                        raise PerplexityError("Rate limit exceeded for Perplexity API")
                    
                    response.raise_for_status()
                    result = await response.json()
                    
                    # Extract image URL from response
                    if isinstance(result, dict) and "data" in result:
                        images = result["data"]
                        if images and len(images) > 0:
                            image_url = images[0].get("url")
                            if image_url:
                                logger.info(f"✅ Perplexity image generated successfully: {image_url}")
                                return image_url
                    
                    logger.warning(f"Perplexity API returned unexpected format: {result}")
                    return None
                    
        except aiohttp.ClientError as e:
            logger.warning(f"Perplexity image API error on attempt {attempt}: {e}")
            if attempt < max_retries:
                await asyncio.sleep(2 ** attempt)
                continue
            raise PerplexityError(f"Image generation failed: {str(e)}")
        except asyncio.TimeoutError as e:
            logger.warning(f"Perplexity image API timeout on attempt {attempt}")
            if attempt < max_retries:
                await asyncio.sleep(2 ** attempt)
                continue
            raise PerplexityError(f"Image generation timeout: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in Perplexity image generation: {e}", exc_info=True)
            raise PerplexityError(f"Image generation failed: {str(e)}")
    
    logger.error("Failed to generate image after all retries")
    return None


async def generate_text(prompt: str, model: str = 'sonar-large') -> Optional[str]:
    """
    Generate text using Perplexity's text generation API.
    
    Args:
        prompt: The text prompt for content generation
        model: The model to use (default: 'sonar-large')
        
    Returns:
        str: Generated text content, or None if generation failed
        
    Raises:
        PerplexityError: If API request fails after retries
    """
    logger.info(f"Generating text with Perplexity: prompt='{_truncate_prompt(prompt)}', model='{model}'")
    
    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {config.pplx_api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": model,
        "messages": [
            {"role": "system", "content": "SMM-копирайтер Telegram. 200-300 слов, эмодзи, структура, CTA."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": config.max_tokens,
        "temperature": config.temperature,
        "stream": False
    }
    
    max_retries = 3
    timeout = aiohttp.ClientTimeout(total=config.api_timeout)
    
    for attempt in range(1, max_retries + 1):
        try:
            logger.debug(f"Perplexity text API request attempt {attempt}/{max_retries}")
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, headers=headers, json=data) as response:
                    status = response.status
                    logger.debug(f"Perplexity text API response: status={status}")
                    
                    if status == 401:
                        logger.error("Perplexity API: Invalid API key (401 Unauthorized)")
                        raise PerplexityError("Invalid Perplexity API key")
                    
                    if status == 429:
                        logger.warning(f"Perplexity API: Rate limit exceeded (429 Too Many Requests)")
                        if attempt < max_retries:
                            await asyncio.sleep(2 ** attempt)
                            continue
                        raise PerplexityError("Rate limit exceeded for Perplexity API")
                    
                    response.raise_for_status()
                    result = await response.json()
                    
                    # Extract text from response
                    if isinstance(result, dict) and "choices" in result:
                        choices = result["choices"]
                        if choices and len(choices) > 0:
                            content = choices[0].get("message", {}).get("content", "").strip()
                            if content:
                                logger.info(f"✅ Perplexity text generated successfully: {len(content)} chars")
                                return content
                    
                    logger.warning(f"Perplexity API returned unexpected format: {result}")
                    return None
                    
        except aiohttp.ClientError as e:
            logger.warning(f"Perplexity text API error on attempt {attempt}: {e}")
            if attempt < max_retries:
                await asyncio.sleep(2 ** attempt)
                continue
            raise PerplexityError(f"Text generation failed: {str(e)}")
        except asyncio.TimeoutError as e:
            logger.warning(f"Perplexity text API timeout on attempt {attempt}")
            if attempt < max_retries:
                await asyncio.sleep(2 ** attempt)
                continue
            raise PerplexityError(f"Text generation timeout: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in Perplexity text generation: {e}", exc_info=True)
            raise PerplexityError(f"Text generation failed: {str(e)}")
    
    logger.error("Failed to generate text after all retries")
    return None
