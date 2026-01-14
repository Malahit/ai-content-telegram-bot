"""
Perplexity API client module for AI Content Telegram Bot.

This module handles all interactions with the Perplexity API,
including error handling, retries, and response processing.
"""

import requests
from typing import Optional, Dict, Any
from logger_config import logger
from config import config


class PerplexityAPIError(Exception):
    """Custom exception for Perplexity API errors."""
    pass


class PerplexityAPIClient:
    """
    Client for interacting with Perplexity API.
    
    Handles API requests with proper error handling, retries,
    and response validation.
    """
    
    API_URL = "https://api.perplexity.ai/chat/completions"
    
    def __init__(self):
        """Initialize the API client."""
        self.api_key = config.pplx_api_key
        self.timeout = config.api_timeout
        self.max_retries = 3
    
    def _build_headers(self) -> Dict[str, str]:
        """
        Build request headers with authorization.
        
        Returns:
            Dict[str, str]: Request headers
        """
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def _build_request_data(
        self,
        topic: str,
        rag_context: str = "",
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Build request data for API call.
        
        Args:
            topic: Topic for content generation
            rag_context: Optional RAG context to include
            max_tokens: Maximum tokens for response
            temperature: Temperature for response generation
            
        Returns:
            Dict[str, Any]: Request data
        """
        max_tokens = max_tokens or config.max_tokens
        temperature = temperature or config.temperature
        
        system_message = "SMM-копирайтер Telegram. 200-300 слов, эмодзи, структура, CTA."
        user_message = f"{rag_context}\n\nПост про: {topic}" if rag_context else f"Пост про: {topic}"
        
        return {
            "model": config.api_model,
            "messages": [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False
        }
    
    def generate_content(
        self,
        topic: str,
        rag_context: str = "",
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Generate content using Perplexity API.
        
        Args:
            topic: Topic for content generation
            rag_context: Optional RAG context to include
            max_tokens: Maximum tokens for response
            
        Returns:
            str: Generated content
            
        Raises:
            PerplexityAPIError: If API request fails after retries
        """
        logger.info(f"Generating content for topic: {topic}")
        
        headers = self._build_headers()
        data = self._build_request_data(topic, rag_context, max_tokens)
        
        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.debug(f"API request attempt {attempt}/{self.max_retries}")
                
                response = requests.post(
                    self.API_URL,
                    headers=headers,
                    json=data,
                    timeout=self.timeout
                )
                
                logger.debug(f"API response status: {response.status_code}")
                response.raise_for_status()
                
                content = self._extract_content(response.json())
                logger.info("Content generated successfully")
                return content
                
            except requests.exceptions.Timeout as e:
                last_error = e
                logger.warning(f"API timeout on attempt {attempt}: {str(e)}")
                
            except requests.exceptions.HTTPError as e:
                last_error = e
                logger.error(f"API HTTP error on attempt {attempt}: {response.status_code} - {str(e)}")
                
                # Don't retry on client errors (4xx)
                if 400 <= response.status_code < 500:
                    break
                    
            except requests.exceptions.RequestException as e:
                last_error = e
                logger.error(f"API request error on attempt {attempt}: {str(e)}")
            
            except Exception as e:
                last_error = e
                logger.error(f"Unexpected error on attempt {attempt}: {str(e)}")
                break
        
        # All retries failed
        error_msg = f"API request failed after {self.max_retries} attempts: {str(last_error)[:100]}"
        logger.error(error_msg)
        raise PerplexityAPIError(error_msg)
    
    def _extract_content(self, response_data: Dict[str, Any]) -> str:
        """
        Extract content from API response.
        
        Args:
            response_data: API response JSON
            
        Returns:
            str: Extracted content
            
        Raises:
            PerplexityAPIError: If content extraction fails
        """
        try:
            content = response_data["choices"][0]["message"]["content"].strip()
            if not content:
                raise PerplexityAPIError("Empty content received from API")
            return content
        except (KeyError, IndexError) as e:
            logger.error(f"Failed to extract content from response: {e}")
            raise PerplexityAPIError(f"Invalid API response structure: {e}")


# Global API client instance
api_client = PerplexityAPIClient()
