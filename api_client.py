import httpx
import logging
import os
import json
from config import config
from logger_config import logger
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from typing import Optional, Dict, Any


class PerplexityAPIError(Exception):
    """Exception raised for Perplexity API errors."""
    pass


class PerplexityAPIClient:
    """
    Client for interacting with Perplexity API.
    
    Handles content generation with retry logic and error handling.
    """
    
    def __init__(self):
        """Initialize the Perplexity API client."""
        self.api_url = "https://api.perplexity.ai/chat/completions"
        self.api_key = config.pplx_api_key
        self.timeout = config.api_timeout
        self.max_tokens = config.max_tokens
        self.temperature = config.temperature
        self.model = config.api_model
        
    def _build_headers(self) -> Dict[str, str]:
        """Build request headers."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def _build_request_data(self, topic: str, rag_context: Optional[str] = None, 
                           max_tokens: Optional[int] = None) -> Dict[str, Any]:
        """
        Build request data for API call.
        
        Args:
            topic: The topic to generate content about
            rag_context: Optional RAG context to include
            max_tokens: Optional max tokens override
            
        Returns:
            Dict containing the request payload
        """
        # Build user message with optional RAG context
        if rag_context:
            user_message = f"Контекст из базы знаний:\n{rag_context}\n\nТема: {topic}"
        else:
            user_message = topic
            
        return {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "Ты - профессиональный контент-мейкер. Создавай интересный и полезный контент."
                },
                {
                    "role": "user",
                    "content": user_message
                }
            ],
            "max_tokens": max_tokens or self.max_tokens,
            "temperature": self.temperature
        }
    
    def _extract_content(self, response_data: Dict[str, Any]) -> str:
        """
        Extract content from API response.
        
        Args:
            response_data: The API response data
            
        Returns:
            str: The extracted content
            
        Raises:
            PerplexityAPIError: If content extraction fails
        """
        try:
            content = response_data['choices'][0]['message']['content'].strip()
            if not content:
                raise PerplexityAPIError("Empty content received from API")
            return content
        except (KeyError, IndexError) as e:
            logger.error(f"Failed to extract content from response: {e}")
            raise PerplexityAPIError(f"Invalid response structure: {e}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.RequestError)),
        before_sleep=lambda retry_state: logger.warning(
            f"Retry attempt {retry_state.attempt_number}/3"
        )
    )
    async def generate_content(self, topic: str, rag_context: Optional[str] = None,
                              max_tokens: Optional[int] = None) -> str:
        """
        Generate content for a given topic using Perplexity API.
        
        This method includes:
        - Retry logic with exponential backoff
        - Special handling for HTTP 429 (rate limit) errors
        - Proper error handling and logging
        
        Args:
            topic: The topic to generate content about
            rag_context: Optional RAG context to include
            max_tokens: Optional max tokens override
            
        Returns:
            str: Generated content
            
        Raises:
            PerplexityAPIError: If content generation fails after retries
        """
        headers = self._build_headers()
        data = self._build_request_data(topic, rag_context, max_tokens)
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.api_url,
                    headers=headers,
                    json=data
                )
                
                # Special handling for HTTP 429 (Rate Limit)
                if response.status_code == 429:
                    # Extract retry-after header if available
                    retry_after = response.headers.get('retry-after', '60')
                    try:
                        delay = int(retry_after)
                    except ValueError:
                        delay = 60
                    
                    error_msg = f"⏳ Perplexity API перегружен. Повторная попытка через {delay} секунд..."
                    logger.warning(error_msg)
                    raise PerplexityAPIError(error_msg)
                
                # Raise an exception for HTTP errors
                response.raise_for_status()
                
                # Extract and return content
                response_data = response.json()
                return self._extract_content(response_data)
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error occurred: {e.response.status_code}")
            raise PerplexityAPIError(f"HTTP error: {e.response.status_code}")
        except httpx.RequestError as e:
            logger.error(f"Request error occurred: {e}")
            raise PerplexityAPIError(f"Request error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during content generation: {e}")
            raise PerplexityAPIError(f"Unexpected error: {e}")


# Global API client instance
api_client = PerplexityAPIClient()