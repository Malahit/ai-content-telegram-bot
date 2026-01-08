#!/usr/bin/env python3
"""
🧪 Test script for content sanitization functionality
Tests the sanitize_content function with various input patterns
"""

import re

def sanitize_content(content: str) -> str:
    """
    🧹 Clean up generated content by removing links and metadata artifacts.
    Removes patterns like [text], (numbers), URLs, and citation markers.
    """
    # Remove markdown links [text](url) and [text]
    content = re.sub(r'\[([^\]]+)\]\([^\)]*\)', r'\1', content)  # Keep text from [text](url)
    content = re.sub(r'\[([^\]]+)\]', '', content)  # Remove standalone [text]
    
    # Remove citation numbers and patterns like (1), (123), [1], etc.
    content = re.sub(r'\(\d+\)', '', content)
    content = re.sub(r'\[\d+\]', '', content)
    
    # Remove standalone URLs
    content = re.sub(r'https?://\S+', '', content)
    
    # Clean up multiple spaces that might result from removals (but preserve newlines)
    lines = content.split('\n')
    lines = [re.sub(r'\s+', ' ', line).strip() for line in lines]
    content = '\n'.join(lines)
    
    # Clean up excessive empty lines
    content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)
    
    return content.strip()


def run_tests():
    """Run comprehensive tests on the sanitize_content function"""
    
    test_cases = [
        # Test case 1: Remove citation numbers in parentheses
        {
            "input": "This is a sentence (1) with citation (2) numbers.",
            "expected": "This is a sentence with citation numbers.",
            "description": "Remove citation numbers in parentheses"
        },
        # Test case 2: Remove citation numbers in brackets
        {
            "input": "This is a sentence [1] with citation [2] numbers.",
            "expected": "This is a sentence with citation numbers.",
            "description": "Remove citation numbers in brackets"
        },
        # Test case 3: Remove URLs
        {
            "input": "Check out https://example.com for more info. Also see http://test.org",
            "expected": "Check out for more info. Also see",
            "description": "Remove standalone URLs"
        },
        # Test case 4: Remove markdown links but keep text
        {
            "input": "Visit [Google](https://google.com) for search.",
            "expected": "Visit Google for search.",
            "description": "Keep text from markdown links"
        },
        # Test case 5: Remove standalone brackets
        {
            "input": "This has [some text] in brackets.",
            "expected": "This has in brackets.",
            "description": "Remove standalone bracket text"
        },
        # Test case 6: Complex case with multiple artifacts
        {
            "input": "🚀 SMM в Москве (1) это круто [2]! Подробнее на https://example.com и [источник](http://test.com)",
            "expected": "🚀 SMM в Москве это круто! Подробнее на и источник",
            "description": "Complex case with citations, URLs, and links"
        },
        # Test case 7: Multiple spaces and newlines cleanup
        {
            "input": "Text with   multiple    spaces\n\n\n\nand newlines",
            "expected": "Text with multiple spaces\n\nand newlines",
            "description": "Clean up excessive spaces and newlines"
        },
        # Test case 8: Mixed case - keep regular parentheses with text
        {
            "input": "This (example) should stay but (123) should go.",
            "expected": "This (example) should stay but should go.",
            "description": "Keep text in parentheses, remove only numbers"
        },
        # Test case 9: Real-world example
        {
            "input": """📱 SMM для бизнеса в Москве (1)

Социальные сети — мощный инструмент [2] для продвижения. 
Узнайте больше на https://example.com/smm

✅ Преимущества:
• Охват аудитории [источник](https://test.org)
• Прямая коммуникация (3)
• Аналитика в реальном времени

🚀 Начните сегодня!""",
            "expected": """📱 SMM для бизнеса в Москве

Социальные сети — мощный инструмент для продвижения. Узнайте больше на

✅ Преимущества: • Охват аудитории • Прямая коммуникация • Аналитика в реальном времени

🚀 Начните сегодня!""",
            "description": "Real-world social media post example"
        }
    ]
    
    print("🧪 Running Content Sanitization Tests\n" + "="*60)
    
    passed = 0
    failed = 0
    
    for i, test in enumerate(test_cases, 1):
        result = sanitize_content(test["input"])
        
        # Normalize whitespace for comparison
        result_normalized = ' '.join(result.split())
        expected_normalized = ' '.join(test["expected"].split())
        
        if result_normalized == expected_normalized:
            print(f"✅ Test {i}: PASSED - {test['description']}")
            passed += 1
        else:
            print(f"❌ Test {i}: FAILED - {test['description']}")
            print(f"   Input:    {test['input'][:80]}...")
            print(f"   Expected: {test['expected'][:80]}...")
            print(f"   Got:      {result[:80]}...")
            failed += 1
    
    print("\n" + "="*60)
    print(f"📊 Results: {passed} passed, {failed} failed out of {passed + failed} tests")
    
    if failed == 0:
        print("🎉 All tests passed!")
        return True
    else:
        print("⚠️ Some tests failed. Review the output above.")
        return False


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)
