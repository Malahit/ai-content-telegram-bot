"""
Test content sanitization functionality
"""
import re
from bs4 import BeautifulSoup

def sanitize_content(content: str) -> str:
    """Clean generated content by removing citation artifacts and URLs."""
    content = re.sub(r'\(\d+\)', '', content)
    content = re.sub(r'\[\d+\]', '', content)
    content = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', content)
    content = re.sub(r'https?://[^\s]+', '', content)
    content = re.sub(r'\[\]', '', content)
    content = re.sub(r'\s+', ' ', content)
    content = re.sub(r'\s+([.,!?])', r'\1', content)
    content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)
    return content.strip()

def safe_html(content: str) -> str:
    """
    Sanitize HTML content for safe Telegram display.
    
    Removes or unwraps unsupported HTML tags and attributes to prevent
    TelegramBadRequest errors from malformed tags like <1>, <2>, etc.
    """
    # First, remove invalid tags like <1>, <2>, <123>, etc. before BeautifulSoup processing
    # This prevents them from being HTML-escaped
    content = re.sub(r'</?(\d+)[^>]*>', '', content)
    
    # Parse the content with BeautifulSoup
    soup = BeautifulSoup(content, 'html.parser')
    
    # Allowed tags for Telegram HTML formatting
    allowed_tags = ['b', 'i', 'u', 's', 'code', 'pre', 'a', 'strong', 'em']
    
    # Remove or unwrap unsupported tags
    for tag in soup.find_all(True):
        if tag.name not in allowed_tags:
            # Unwrap the tag (keep content, remove tag)
            tag.unwrap()
        elif tag.name == 'a':
            # For anchor tags, unwrap if no valid href attribute
            href = tag.get('href', '')
            if not href or href == '#':
                tag.unwrap()
            else:
                # Keep only href attribute for valid links
                tag.attrs = {'href': href}
    
    # Convert back to string
    cleaned = str(soup)
    
    # Remove any remaining HTML-like patterns that aren't valid tags
    # This catches remaining unsupported tags
    cleaned = re.sub(r'<(?![/]?(?:b|i|u|s|code|pre|a|strong|em)(?:\s|>))[^>]*>', '', cleaned)
    
    return cleaned

def test_sanitization():
    tests = [
        ("This is a test (1) with citations (123).", "This is a test with citations."),
        ("Text with [1] and [12] references.", "Text with and references."),
        ("Check out [this link](https://example.com) for more info.", "Check out this link for more info."),
        ("Visit https://example.com for details.", "Visit for details."),
        ("📱 SMM в Москве (1) [2]! Подробнее https://example.com [источник](http://test.org).", "📱 SMM в Москве! Подробнее источник."),
        ("Text   with    lots    of     spaces", "Text with lots of spaces")
    ]
    
    for i, (input_text, expected) in enumerate(tests, 1):
        result = sanitize_content(input_text)
        assert result == expected, f"Test {i} failed: got '{result}', expected '{expected}'"
        print(f"✅ Test {i} passed")
    
    print("\n✅ All sanitization tests passed!")

def test_html_sanitization():
    """Test HTML sanitization for Telegram-safe output"""
    tests = [
        # Test malformed tags like <1>, <2>
        ("This is <1>text</1> with bad tags", "This is text with bad tags"),
        # OL/LI tags are unwrapped, content is preserved
        ("List: <ol><li>1. Item</li></ol>", "List: 1. Item"),
        # Test allowed tags
        ("This is <b>bold</b> text", "This is <b>bold</b> text"),
        ("This is <i>italic</i> and <u>underlined</u>", "This is <i>italic</i> and <u>underlined</u>"),
        # Test unsupported tags - should be unwrapped
        ("Text with <div>div</div> and <span>span</span>", "Text with div and span"),
        ("Text with <h1>heading</h1>", "Text with heading"),
        # Test links - valid links preserved, invalid unwrapped
        ('<a href="https://example.com">link</a>', '<a href="https://example.com">link</a>'),
        ('<a>link without href</a>', 'link without href'),
        ('<a href="#">link with # href</a>', 'link with # href'),
        # Test mixed content
        ("Text <1>with</1> <b>bold</b> and <div>div</div>", "Text with <b>bold</b> and div"),
        # Test nested tags - valid tags inside invalid tags should be preserved
        ("<1><b>bold text</b></1>", "<b>bold text</b>"),
        ("<div><i>italic</i> and <u>underline</u></div>", "<i>italic</i> and <u>underline</u>"),
    ]
    
    for i, (input_text, expected) in enumerate(tests, 1):
        result = safe_html(input_text)
        assert result == expected, f"HTML Test {i} failed: got '{result}', expected '{expected}'"
        print(f"✅ HTML Test {i} passed")
    
    print("\n✅ All HTML sanitization tests passed!")

if __name__ == "__main__":
    test_sanitization()
    test_html_sanitization()
