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
    # Clean up multiple line breaks (must happen before general whitespace cleanup)
    content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)
    # Clean up excessive whitespace (but preserve newlines)
    content = re.sub(r'[^\S\n]+', ' ', content)
    content = re.sub(r'\s+([.,!?])', r'\1', content)
    return content.strip()

def test_sanitization():
    """Test content sanitization with various input patterns."""
    tests = [
        # Basic citation removal
        ("This is a test (1) with citations (123).", "This is a test with citations."),
        ("Text with [1] and [12] references.", "Text with and references."),
        
        # Markdown link removal
        ("Check out [this link](https://example.com) for more info.", "Check out this link for more info."),
        
        # URL removal
        ("Visit https://example.com for details.", "Visit for details."),
        
        # Complex case with multiple artifacts
        ("📱 SMM в Москве (1) [2]! Подробнее https://example.com [источник](http://test.org).", "📱 SMM в Москве! Подробнее источник."),
        
        # Whitespace normalization
        ("Text   with    lots    of     spaces", "Text with lots of spaces"),
        
        # Multiple consecutive citations
        ("Text (1)(2)(3) more text", "Text more text"),
        
        # Mixed citation formats
        ("Sample (10) text [20] here (30)", "Sample text here"),
        
        # URL with query parameters
        ("Link https://example.com?foo=bar&baz=qux here", "Link here"),
        
        # Empty brackets cleanup
        ("Text with [] empty [] brackets", "Text with empty brackets"),
        
        # Multiple line breaks
        ("Line 1\n\n\n\nLine 2", "Line 1\n\nLine 2"),
        
        # Punctuation spacing
        ("Word  ,  text  .  end  !", "Word, text. end!"),
        
        # Leading/trailing whitespace
        ("  Content with spaces  ", "Content with spaces"),
        
        # No changes needed
        ("Simple text without artifacts", "Simple text without artifacts"),
        
        # Empty input
        ("", ""),
        
        # Only whitespace
        ("   ", ""),
        
        # Multiple URLs
        ("Visit https://site1.com and https://site2.com for info", "Visit and for info"),
        
        # Nested markdown links
        ("[Link1](https://url1.com) and [Link2](https://url2.com)", "Link1 and Link2"),
    ]
    
    passed = 0
    failed = 0
    
    for i, (input_text, expected) in enumerate(tests, 1):
        result = sanitize_content(input_text)
        if result == expected:
            print(f"✅ Test {i} passed")
            passed += 1
        else:
            print(f"❌ Test {i} failed:")
            print(f"   Input:    {repr(input_text)}")
            print(f"   Expected: {repr(expected)}")
            print(f"   Got:      {repr(result)}")
            failed += 1
    
    print(f"\n{'='*60}")
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)} tests")
    
    if failed > 0:
        raise AssertionError(f"{failed} test(s) failed")
    
    print("✅ All sanitization tests passed!")

if __name__ == "__main__":
    test_sanitization()
