# GitHub Copilot TASK:
# 1. Добавь retry-логику для метода generate_content через tenacity:
#    - stop=stop_after_attempt(3)
#    - wait=wait_exponential(multiplier=1, min=2, max=10)
#    - retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.RequestError))
# 2. Для ошибки 429 (Rate Limit):
#    - Используй заголовок "Retry-After" из ответа
#    - Добавь логирование: logger.warning(f"⏳ Perplexity перегружен. Повтор через {delay} сек...")
# 3. Сохрани существующую логику:
#    - Использование PPLX_API_KEY из config
#    - Асинхронные запросы через httpx.AsyncClient
#    - Формат ответа: {"content": "...", "sources": [...]}
# 4. Добавь импорт: from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
# 5. НЕ изменяй сигнатуру метода generate_content
# 6. НЕ удаляй существующие импорты и функции
# This is a placeholder content of the api_client.py for fetching and updating it.