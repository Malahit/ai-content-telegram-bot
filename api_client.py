import httpx
import logging
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, before_sleep_log
from config import config
from logger_config import logger

class APIClient:
    def __init__(self):
        self.pplx_api_key = config.PPLX_API_KEY
        self.client = httpx.AsyncClient(timeout=30.0)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.RequestError)),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    async def generate_content(self, prompt: str, model: str = "sonar-small-online") -> dict:
        url = "https://api.perplexity.ai/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.pplx_api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "return_citations": True
        }
        
        try:
            response = await self.client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            sources = []
            
            if "citations" in data:
                sources = [
                    f"[{i+1}] {cite['title']}: {cite['url']}" 
                    for i, cite in enumerate(data["citations"])
                ]
            
            return {
                "content": content,
                "sources": sources
            }
        
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                retry_after = int(e.response.headers.get("Retry-After", 5))
                logger.warning(f"⏳ Perplexity API перегружен. Запрос будет повторен через {retry_after} сек...")
                # Tenacity автоматически обработает retry благодаря декоратору
            elif e.response.status_code == 401:
                logger.critical("❌ Неверный API-ключ Perplexity!")
                return {"content": "❌ Ошибка авторизации Perplexity API. Обратитесь к администратору.", "sources": []}
            
            raise  # Передаем исключение в tenacity для retry
        
        except Exception as e:
            logger.exception("💥 Критическая ошибка в generate_content")
            return {"content": f"❌ Системная ошибка: {str(e)}", "sources": []}
    
    async def close(self):
        await self.client.aclose()