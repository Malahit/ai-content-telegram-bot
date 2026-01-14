"""
Unit tests for translation service module.

Tests translation functionality, language detection, and error handling.
"""

import unittest
from unittest.mock import patch, Mock
import asyncio


class TestTranslationService(unittest.TestCase):
    """Test cases for TranslationService."""
    
    def test_translation_disabled_when_libraries_unavailable(self):
        """Test that translation is disabled when libraries are not available."""
        with patch.dict('sys.modules', {'langdetect': None, 'deep_translator': None}):
            # Re-import to trigger ImportError
            import importlib
            import translation_service
            importlib.reload(translation_service)
            
            self.assertFalse(translation_service.TRANSLATE_ENABLED)
    
    @patch('translation_service.TRANSLATE_ENABLED', True)
    @patch('translation_service.GoogleTranslator')
    def test_is_enabled(self, mock_translator):
        """Test is_enabled method."""
        from translation_service import TranslationService
        
        service = TranslationService()
        self.assertTrue(service.is_enabled())
    
    @patch('translation_service.TRANSLATE_ENABLED', True)
    @patch('translation_service.detect')
    @patch('translation_service.GoogleTranslator')
    def test_detect_and_translate_english_text(self, mock_translator_class, mock_detect):
        """Test translation of English text to Russian."""
        from translation_service import TranslationService
        
        # Setup mocks
        mock_detect.return_value = 'en'
        mock_translator = Mock()
        mock_translator.translate.return_value = 'Привет мир'
        mock_translator_class.return_value = mock_translator
        
        service = TranslationService()
        
        # Run async test
        async def run_test():
            translated, lang = await service.detect_and_translate('Hello world')
            self.assertEqual(translated, 'Привет мир')
            self.assertEqual(lang, 'en')
        
        asyncio.run(run_test())
    
    @patch('translation_service.TRANSLATE_ENABLED', True)
    @patch('translation_service.detect')
    @patch('translation_service.GoogleTranslator')
    def test_detect_and_translate_russian_text_no_translation(self, mock_translator_class, mock_detect):
        """Test that Russian text is not translated."""
        from translation_service import TranslationService
        
        # Setup mocks
        mock_detect.return_value = 'ru'
        mock_translator = Mock()
        mock_translator_class.return_value = mock_translator
        
        service = TranslationService()
        
        # Run async test
        async def run_test():
            translated, lang = await service.detect_and_translate('Привет мир')
            self.assertEqual(translated, 'Привет мир')
            self.assertEqual(lang, 'ru')
            # Translator should not be called for Russian text
            mock_translator.translate.assert_not_called()
        
        asyncio.run(run_test())
    
    @patch('translation_service.TRANSLATE_ENABLED', True)
    @patch('translation_service.detect')
    @patch('translation_service.GoogleTranslator')
    def test_detect_and_translate_error_fallback(self, mock_translator_class, mock_detect):
        """Test that errors in translation fall back gracefully."""
        from translation_service import TranslationService
        
        # Setup mocks to raise error
        mock_detect.side_effect = Exception('Detection error')
        mock_translator = Mock()
        mock_translator_class.return_value = mock_translator
        
        service = TranslationService()
        
        # Run async test
        async def run_test():
            original_text = 'Test text'
            translated, lang = await service.detect_and_translate(original_text)
            # Should return original text on error
            self.assertEqual(translated, original_text)
            self.assertEqual(lang, 'ru')
        
        asyncio.run(run_test())
    
    @patch('translation_service.TRANSLATE_ENABLED', False)
    def test_detect_and_translate_disabled(self):
        """Test behavior when translation is disabled."""
        from translation_service import TranslationService
        
        service = TranslationService()
        
        # Run async test
        async def run_test():
            translated, lang = await service.detect_and_translate('Hello world')
            self.assertEqual(translated, 'Hello world')
            self.assertEqual(lang, 'ru')
        
        asyncio.run(run_test())
    
    @patch('translation_service.TRANSLATE_ENABLED', True)
    @patch('translation_service.GoogleTranslator')
    def test_add_language_marker(self, mock_translator_class):
        """Test adding language marker to text."""
        from translation_service import TranslationService
        
        mock_translator = Mock()
        mock_translator_class.return_value = mock_translator
        
        service = TranslationService()
        
        # Test with English
        marked = service.add_language_marker('Hello', 'en')
        self.assertIn('[EN]', marked)
        
        # Test with Russian (no marker)
        marked = service.add_language_marker('Привет', 'ru')
        self.assertEqual(marked, 'Привет')


if __name__ == '__main__':
    unittest.main()
