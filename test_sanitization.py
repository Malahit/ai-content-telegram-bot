"""
Test content sanitization functionality
"""
import re

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

if __name__ == "__main__":
    test_sanitization()
