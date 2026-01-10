"""
SEO post generator module.
Generates SEO-optimized posts with structured content based on Yandex Wordstat data.
"""
import logging
import requests
from typing import Dict, Any

logger = logging.getLogger(__name__)


class SEOPostGenerator:
    """Generates SEO-optimized posts using Perplexity API"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.api_url = "https://api.perplexity.ai/chat/completions"
    
    def _calculate_keyword_count(self, text: str, keyword: str) -> int:
        """Calculate how many times keyword appears in text"""
        return text.lower().count(keyword.lower())
    
    def _build_seo_prompt(self, keyword: str, wordstat_data: Dict[str, Any]) -> str:
        """
        Build SEO post generation prompt with keyword data
        
        Args:
            keyword: Main keyword
            wordstat_data: Wordstat data including related keywords
            
        Returns:
            Formatted prompt string
        """
        related_keywords = wordstat_data.get("related_keywords", [])
        search_volume = wordstat_data.get("search_volume", "N/A")
        
        # Build related keywords list
        related_kw_text = ""
        if related_keywords:
            related_kw_text = "\nРодственные запросы: " + ", ".join(related_keywords[:5])
        
        prompt = f"""Создай SEO-оптимизированный пост для Telegram на тему: "{keyword}"

Статистика Яндекс.Вордстат:
- Запросов в месяц: {search_volume}{related_kw_text}

ВАЖНЫЕ ТРЕБОВАНИЯ:
1. Объем: 300 слов
2. Структура:
   - H1 заголовок (начинается с #)
   - 2-3 H2 подзаголовка (начинаются с ##)
   - Списки (маркированные или нумерованные)
3. Плотность ключевого слова "{keyword}": 1.5% (около 4-5 раз в тексте из 300 слов)
4. Используй эмодзи для привлекательности
5. Добавь CTA (призыв к действию) в конце
6. Включи родственные запросы естественным образом в текст

Формат:
- Используй HTML-разметку для Telegram: <b>жирный</b>, <i>курсив</i>
- Заголовки обозначай символами # (H1) и ## (H2)
- Избегай markdown ссылок, используй только текст

Пиши профессионально, информативно и увлекательно!"""
        
        return prompt
    
    def generate_seo_post(self, keyword: str, wordstat_data: Dict[str, Any]) -> str:
        """
        Generate SEO-optimized post using Perplexity API
        
        Args:
            keyword: Main keyword
            wordstat_data: Wordstat data
            
        Returns:
            Generated SEO post content
        """
        try:
            prompt = self._build_seo_prompt(keyword, wordstat_data)
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": "sonar",
                "messages": [
                    {
                        "role": "system",
                        "content": "Ты профессиональный SEO-копирайтер. Создаешь структурированный, оптимизированный контент для Telegram с правильной плотностью ключевых слов."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": 1000,
                "temperature": 0.7,
                "stream": False
            }
            
            logger.info(f"Generating SEO post for keyword: {keyword}")
            response = requests.post(
                self.api_url,
                headers=headers,
                json=data,
                timeout=45
            )
            response.raise_for_status()
            
            content = response.json()["choices"][0]["message"]["content"].strip()
            
            # Add SEO metadata footer
            search_volume = wordstat_data.get("search_volume", "N/A")
            related_count = len(wordstat_data.get("related_keywords", []))
            
            seo_footer = f"\n\n📊 <i>SEO данные:</i>\n"
            seo_footer += f"🔍 Запросов: {search_volume}\n"
            if related_count > 0:
                seo_footer += f"🔗 Связанных тем: {related_count}"
            
            return content + seo_footer
            
        except Exception as e:
            logger.error(f"Error generating SEO post: {e}")
            return f"❌ Ошибка генерации SEO поста: {str(e)[:100]}"
