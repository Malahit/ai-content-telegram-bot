#!/usr/bin/env python3
"""
🎯 Demo script showing the sanitize_content function in action
This demonstrates how the function cleans up generated content
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


# Example: Simulated content from Perplexity API with artifacts
example_content = """
📱 SMM для бизнеса в Москве (1)

Социальные сети — это мощный инструмент [2] для продвижения вашего бизнеса. 
Подробнее читайте на https://example.com/smm-guide

✅ Основные преимущества SMM:

• Широкий охват целевой аудитории [источник](https://marketing-blog.com)
• Прямая коммуникация с клиентами (3)
• Аналитика в реальном времени [4]
• Низкая стоимость по сравнению с традиционной рекламой (5)

💡 Начните продвижение в социальных сетях уже сегодня и увеличьте продажи! 
Больше информации: http://test.org/promo

#SMM #МаркетингМосква #Бизнес
"""

print("="*70)
print("🔥 DEMO: Content Sanitization Function")
print("="*70)
print("\n📝 ORIGINAL CONTENT (with artifacts):\n")
print(example_content)
print("\n" + "="*70)
print("\n🧹 SANITIZED CONTENT (cleaned):\n")

cleaned = sanitize_content(example_content)
print(cleaned)

print("\n" + "="*70)
print("✅ Artifacts removed:")
print("   • Citation numbers: (1), (3), (5), [2], [4]")
print("   • URLs: https://example.com/smm-guide, http://test.org/promo")
print("   • Markdown links: [источник](https://marketing-blog.com)")
print("\n💡 The content is now clean and ready for posting!")
print("="*70)
