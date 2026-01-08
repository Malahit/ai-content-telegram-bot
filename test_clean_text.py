"""
Test script for the clean_text function.
Validates text sanitization for common cases.
"""
import re


def clean_text(content: str) -> str:
    """🧹 Sanitize generated content by removing artifacts"""
    # Remove links starting with http or www
    content = re.sub(r"https?://\S+|www\.\S+", "", content)
    # Remove numbers in brackets or parentheses (e.g., [123] or (123))
    content = re.sub(r"\[\d+\]|\(\d+\)", "", content)
    # Remove extra spaces and trim
    content = re.sub(r"\s+", " ", content).strip()
    return content


def test_clean_text():
    """Run test cases for clean_text function"""
    tests = [
        {
            "name": "Remove HTTP links",
            "input": "Check this out https://example.com for more info",
            "expected": "Check this out for more info"
        },
        {
            "name": "Remove HTTPS links",
            "input": "Visit https://www.example.com/page for details",
            "expected": "Visit for details"
        },
        {
            "name": "Remove www links",
            "input": "Go to www.example.com for more",
            "expected": "Go to for more"
        },
        {
            "name": "Remove numbers in square brackets",
            "input": "This is a citation [123] from a source",
            "expected": "This is a citation from a source"
        },
        {
            "name": "Remove numbers in parentheses",
            "input": "This is a reference (456) to check",
            "expected": "This is a reference to check"
        },
        {
            "name": "Remove multiple bracket citations",
            "input": "First [1] and second [2] citations here",
            "expected": "First and second citations here"
        },
        {
            "name": "Remove extra whitespace",
            "input": "Too   many    spaces   here",
            "expected": "Too many spaces here"
        },
        {
            "name": "Trim leading and trailing whitespace",
            "input": "   Extra spaces at start and end   ",
            "expected": "Extra spaces at start and end"
        },
        {
            "name": "Complex case with all artifacts",
            "input": "Visit https://example.com [1] for details  (2)  and www.test.com  has more   info",
            "expected": "Visit for details and has more info"
        },
        {
            "name": "Text with no artifacts",
            "input": "Clean text without any links or citations",
            "expected": "Clean text without any links or citations"
        },
        {
            "name": "Keep non-numeric brackets",
            "input": "This [note] and (comment) should remain",
            "expected": "This [note] and (comment) should remain"
        },
        {
            "name": "Multiple links in one text",
            "input": "Check http://one.com and https://two.com and www.three.com",
            "expected": "Check and and"
        },
    ]
    
    passed = 0
    failed = 0
    
    print("🧪 Running clean_text tests...\n")
    
    for test in tests:
        result = clean_text(test["input"])
        if result == test["expected"]:
            print(f"✅ PASS: {test['name']}")
            passed += 1
        else:
            print(f"❌ FAIL: {test['name']}")
            print(f"   Input:    '{test['input']}'")
            print(f"   Expected: '{test['expected']}'")
            print(f"   Got:      '{result}'")
            failed += 1
    
    print(f"\n{'='*60}")
    print(f"Total: {len(tests)} | Passed: {passed} | Failed: {failed}")
    print(f"{'='*60}")
    
    return failed == 0


if __name__ == "__main__":
    success = test_clean_text()
    exit(0 if success else 1)
