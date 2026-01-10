"""
Yandex Wordstat parser module using Selenium.
Scrapes search statistics and related keywords from wordstat.yandex.ru
"""
import logging
import time
import re
from typing import Dict, Any, Optional, List
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from wordstat_db import wordstat_db

logger = logging.getLogger(__name__)

# Configuration
WORDSTAT_URL = "https://wordstat.yandex.ru"
DEFAULT_TIMEOUT = 15
MAX_RETRIES = 3


class WordstatParser:
    """Parses Yandex Wordstat data using Selenium WebDriver"""
    
    def __init__(self, headless: bool = True, timeout: int = DEFAULT_TIMEOUT):
        self.headless = headless
        self.timeout = timeout
        self.driver = None
    
    def _init_driver(self):
        """Initialize Chrome WebDriver with appropriate options"""
        try:
            chrome_options = Options()
            if self.headless:
                chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            
            # Use webdriver-manager to automatically handle driver installation
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            logger.info("WebDriver initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing WebDriver: {e}")
            raise
    
    def _close_driver(self):
        """Close WebDriver and clean up resources"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("WebDriver closed successfully")
            except Exception as e:
                logger.error(f"Error closing WebDriver: {e}")
            finally:
                self.driver = None
    
    def _extract_search_volume(self, text: str) -> Optional[str]:
        """
        Extract search volume from text (e.g., '150000' -> '150k/мес')
        
        Args:
            text: Text containing search volume
            
        Returns:
            Formatted search volume string or None
        """
        try:
            # Remove all non-digit characters
            digits = re.sub(r'\D', '', text)
            if not digits:
                return None
            
            volume = int(digits)
            
            # Format based on volume
            if volume >= 1_000_000:
                formatted = f"{volume / 1_000_000:.1f}M"
            elif volume >= 1_000:
                formatted = f"{volume / 1_000:.0f}k"
            else:
                formatted = str(volume)
            
            return f"{formatted}/мес"
        except Exception as e:
            logger.error(f"Error extracting search volume: {e}")
            return None
    
    @retry(
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((TimeoutException, WebDriverException)),
        reraise=True
    )
    def _scrape_wordstat(self, keyword: str) -> Dict[str, Any]:
        """
        Scrape Wordstat data for a keyword (with retry logic)
        
        Args:
            keyword: Search keyword
            
        Returns:
            Dictionary with wordstat data
        """
        if not self.driver:
            self._init_driver()
        
        try:
            # Navigate to Wordstat
            logger.info(f"Navigating to Wordstat for keyword: {keyword}")
            self.driver.get(WORDSTAT_URL)
            
            # Wait for page to load
            time.sleep(2)
            
            # Find search input and enter keyword
            wait = WebDriverWait(self.driver, self.timeout)
            search_input = wait.until(
                EC.presence_of_element_located((By.NAME, "text"))
            )
            search_input.clear()
            search_input.send_keys(keyword)
            
            # Find and click search button
            search_button = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']"))
            )
            search_button.click()
            
            # Wait for results to load
            logger.info("Waiting for results to load...")
            time.sleep(3)
            
            # Extract main search volume
            search_volume = "N/A"
            try:
                # Try to find the main keyword stats
                volume_element = wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".b-word-statistics__td_type_shows"))
                )
                volume_text = volume_element.text.strip()
                search_volume = self._extract_search_volume(volume_text) or volume_text
                logger.info(f"Search volume found: {search_volume}")
            except (TimeoutException, NoSuchElementException):
                logger.warning("Could not find search volume element")
                # Try alternative selectors
                try:
                    stats_elements = self.driver.find_elements(By.CSS_SELECTOR, ".b-word-statistics td")
                    if stats_elements:
                        for elem in stats_elements:
                            text = elem.text.strip()
                            if text and text[0].isdigit():
                                search_volume = self._extract_search_volume(text) or text
                                break
                except Exception as e:
                    logger.error(f"Error with alternative volume extraction: {e}")
            
            # Extract related keywords
            related_keywords = []
            try:
                keyword_elements = self.driver.find_elements(
                    By.CSS_SELECTOR, ".b-word-statistics__phrase"
                )
                for elem in keyword_elements[:10]:  # Limit to top 10
                    kw_text = elem.text.strip()
                    if kw_text and kw_text != keyword:
                        related_keywords.append(kw_text)
                logger.info(f"Found {len(related_keywords)} related keywords")
            except Exception as e:
                logger.error(f"Error extracting related keywords: {e}")
            
            # If we couldn't extract anything meaningful, try a simpler approach
            if search_volume == "N/A" and not related_keywords:
                logger.warning("Minimal data extracted, using fallback approach")
                # Get all text from the page and try to extract any numbers
                page_text = self.driver.find_element(By.TAG_NAME, "body").text
                numbers = re.findall(r'\d[\d\s]*\d|\d+', page_text)
                if numbers:
                    # Use the first significant number found
                    search_volume = self._extract_search_volume(numbers[0]) or numbers[0]
            
            return {
                "keyword": keyword,
                "search_volume": search_volume,
                "related_keywords": related_keywords,
                "timestamp": time.time()
            }
            
        except Exception as e:
            logger.error(f"Error scraping Wordstat: {e}")
            raise
    
    def get_wordstat_data(self, keyword: str, use_cache: bool = True) -> Dict[str, Any]:
        """
        Get Wordstat data for a keyword (checks cache first)
        
        Args:
            keyword: Search keyword
            use_cache: Whether to check cache first
            
        Returns:
            Dictionary with wordstat data
        """
        # Check cache first
        if use_cache:
            cached_data = wordstat_db.get(keyword)
            if cached_data:
                logger.info(f"Using cached data for keyword: {keyword}")
                return cached_data
        
        # Scrape if not in cache or cache disabled
        try:
            logger.info(f"Scraping fresh data for keyword: {keyword}")
            data = self._scrape_wordstat(keyword)
            
            # Save to cache
            wordstat_db.upsert(keyword, data)
            
            return data
        except Exception as e:
            logger.error(f"Failed to get Wordstat data after retries: {e}")
            # Return minimal data structure
            return {
                "keyword": keyword,
                "search_volume": "N/A",
                "related_keywords": [],
                "error": str(e)
            }
        finally:
            self._close_driver()
    
    def __del__(self):
        """Cleanup when object is destroyed"""
        self._close_driver()


# Global instance
wordstat_parser = WordstatParser()
