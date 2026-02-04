"""
API Client module for Perplexity AI API.

Handles content generation with error handling and retry logic.
"""
import httpx
import logging
import re
from typing import Optional, Tuple
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, before_sleep_log
from config import config
from logger_config import logger


class PerplexityAPIError(Exception):
    """Custom exception for Perplexity API errors."""
    pass


class APIClient:
    """Client for interacting with Perplexity AI API."""
    
    def __init__(self):
        """Initialize API client with configuration."""
        self.pplx_api_key = config.pplx_api_key
        self.api_timeout = config.api_timeout
        self.max_tokens = config.max_tokens
        self.temperature = config.temperature
        self.api_model = config.api_model
        self.client = httpx.AsyncClient(timeout=float(self.api_timeout))
    
    def generate_content(self, topic: str, rag_context: Optional[str] = None, max_tokens: Optional[int] = None) -> str:
        """
        Generate content for a topic using Perplexity API (synchronous).
        
        Args:
            topic: Topic to generate content about
            rag_context: Optional RAG context to include
            max_tokens: Optional max tokens override
            
        Returns:
            Generated content as string
            
        Raises:
            PerplexityAPIError: If API request fails
        """
        import asyncio
        
        # Use asyncio.run for synchronous wrapper
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self.generate_content_async(topic, rag_context, max_tokens))
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.RequestError)),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    async def generate_content_async(self, topic: str, rag_context: Optional[str] = None, max_tokens: Optional[int] = None) -> str:
        """
        Generate content for a topic using Perplexity API (async).
        
        Args:
            topic: Topic to generate content about
            rag_context: Optional RAG context to include
            max_tokens: Optional max tokens override
            
        Returns:
            Generated content as string
            
        Raises:
            PerplexityAPIError: If API request fails
        """
        url = "https://api.perplexity.ai/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.pplx_api_key}",
            "Content-Type": "application/json"
        }
        
        # Build prompt with optional RAG context
        if rag_context:
            prompt = f"Context: {rag_context}\n\nTopic: {topic}\n\nGenerate a post about this topic."
        else:
            prompt = f"Generate a post about: {topic}"
        
        payload = {
            "model": self.api_model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens or self.max_tokens,
            "temperature": self.temperature
        }
        
        try:
            response = await self.client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            
            return content
        
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                retry_after = int(e.response.headers.get("Retry-After", 5))
                logger.warning(f"⏳ Perplexity API rate limited. Retrying in {retry_after}s...")
                raise
            elif e.response.status_code == 401:
                logger.critical("❌ Invalid Perplexity API key!")
                raise PerplexityAPIError("Invalid API key")
            else:
                logger.error(f"Perplexity API error: {e.response.status_code}")
                raise PerplexityAPIError(f"API error: {e.response.status_code}")
        
        except Exception as e:
            logger.exception("💥 Critical error in generate_content")
            raise PerplexityAPIError(f"System error: {str(e)}")
    
    async def generate_content_with_keyword(self, topic: str, rag_context: Optional[str] = None, max_tokens: Optional[int] = None) -> Tuple[str, str]:
        """
        Generate content and extract a keyword for photo search using Perplexity API.
        
        Args:
            topic: Topic to generate content about
            rag_context: Optional RAG context to include
            max_tokens: Optional max tokens override
            
        Returns:
            Tuple of (generated_content, photo_keyword)
            
        Raises:
            PerplexityAPIError: If API request fails
        """
        url = "https://api.perplexity.ai/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.pplx_api_key}",
            "Content-Type": "application/json"
        }
        
        # Build prompt that requests both content and keyword
        if rag_context:
            prompt = f"""Context: {rag_context}

Topic: {topic}

Please generate a post about this topic. After the post content, on a new line, provide exactly ONE keyword (in English) that would be best for finding a relevant photo. Format:

POST CONTENT HERE

KEYWORD: <single keyword>"""
        else:
            prompt = f"""Generate a post about: {topic}

After the post content, on a new line, provide exactly ONE keyword (in English) that would be best for finding a relevant photo. Format:

POST CONTENT HERE

KEYWORD: <single keyword>"""
        
        payload = {
            "model": self.api_model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens or self.max_tokens,
            "temperature": self.temperature
        }
        
        try:
            response = await self.client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            full_response = data["choices"][0]["message"]["content"]
            
            # Extract keyword from response
            keyword_match = re.search(r'KEYWORD:\s*([^\n]+)', full_response, re.IGNORECASE)
            if keyword_match:
                keyword = keyword_match.group(1).strip()
                # Remove the keyword line from content
                content = re.sub(r'\n*KEYWORD:\s*[^\n]+\s*$', '', full_response, flags=re.IGNORECASE).strip()
            else:
                # Fallback: extract meaningful keyword from topic
                content = full_response
                # Filter out common stop words and get first meaningful word
                stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with'}
                words = [w for w in topic.split() if w.lower() not in stop_words and len(w) > 2]
                keyword = words[0] if words else topic.split()[0] if topic.split() else "abstract"
            
            logger.info(f"Generated content with keyword: '{keyword}' for topic: '{topic}'")
            return content, keyword
        
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                retry_after = int(e.response.headers.get("Retry-After", 5))
                logger.warning(f"⏳ Perplexity API rate limited. Retrying in {retry_after}s...")
                raise
            elif e.response.status_code == 401:
                logger.critical("❌ Invalid Perplexity API key!")
                raise PerplexityAPIError("Invalid API key")
            else:
                logger.error(f"Perplexity API error: {e.response.status_code}")
                raise PerplexityAPIError(f"API error: {e.response.status_code}")
        
        except Exception as e:
            logger.exception("💥 Critical error in generate_content_with_keyword")
            raise PerplexityAPIError(f"System error: {str(e)}")
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


# Global API client instance
api_client = APIClient()