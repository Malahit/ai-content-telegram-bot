"""
Translation service module for AI Content Telegram Bot.

This module handles language detection and translation functionality
with proper error handling and fallback mechanisms.
"""

from typing import Tuple, Optional
from logger_config import logger


# Try to import translation libraries
try:
    from langdetect import detect, LangDetectException
    from deep_translator import GoogleTranslator
    TRANSLATE_ENABLED = True
except ImportError as e:
    TRANSLATE_ENABLED = False
    logger.warning(f"Translation libraries not available: {e}")


class TranslationService:
    """
    Service for language detection and translation.
    
    Provides automatic translation from English to Russian
    with fallback mechanisms for errors.
    """
    
    def __init__(self):
        """Initialize translation service."""
        self.enabled = TRANSLATE_ENABLED
        if self.enabled:
            try:
                self.translator = GoogleTranslator(source='auto', target='ru')
                logger.info("Translation service initialized successfully")
            except Exception as e:
                self.enabled = False
                logger.error(f"Failed to initialize translator: {e}")
        else:
            self.translator = None
            logger.info("Translation service disabled - libraries not available")
    
    def is_enabled(self) -> bool:
        """
        Check if translation is enabled.
        
        Returns:
            bool: True if translation is available
        """
        return self.enabled
    
    async def detect_and_translate(self, text: str) -> Tuple[str, str]:
        """
        Detect language and translate to Russian if needed.
        
        Args:
            text: Text to detect and translate
            
        Returns:
            Tuple[str, str]: Translated text and detected language code
        """
        if not self.enabled:
            logger.debug("Translation disabled, returning original text")
            return text, 'ru'
        
        try:
            # Detect language
            detected_lang = detect(text)
            logger.debug(f"Detected language: {detected_lang}")
            
            # Translate if English
            if detected_lang == 'en':
                logger.debug("Translating from English to Russian")
                translated = self.translator.translate(text)
                
                if not translated:
                    logger.warning("Translation returned empty string, using original")
                    return text, detected_lang
                
                logger.info(f"Successfully translated text from {detected_lang} to Russian")
                return translated, detected_lang
            
            # Return original if not English
            logger.debug(f"Text already in {detected_lang}, no translation needed")
            return text, detected_lang
            
        except LangDetectException as e:
            logger.warning(f"Language detection failed: {e}, assuming Russian")
            return text, 'ru'
            
        except Exception as e:
            logger.error(f"Translation error: {e}, returning original text")
            return text, 'ru'
    
    def add_language_marker(self, text: str, lang_code: str) -> str:
        """
        Add language marker to text.
        
        Args:
            text: Text to mark
            lang_code: Language code
            
        Returns:
            str: Text with language marker
        """
        if lang_code and lang_code != 'ru':
            return f"{text}\n\n🌐 [{lang_code.upper()}]"
        return text


# Global translation service instance
translation_service = TranslationService()
