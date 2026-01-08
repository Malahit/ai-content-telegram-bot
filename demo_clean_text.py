"""
Manual demonstration of the clean_text function.
This script shows how the function sanitizes text that might come from the API.
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


# Example text that might come from the API with artifacts
example_texts = [
    """
🏋️ Фитнес и Здоровье [1]

Поддержание физической формы - это ключ к здоровой жизни. 
Регулярные тренировки помогают улучшить настроение (2) и общее самочувствие.

Источники: https://example.com/fitness [3]
Подробнее на www.health-info.com
    """,
    """
🍎 Правильное Питание

Здоровое питание включает фрукты, овощи и белки [1]. 
Узнайте больше на https://nutrition.com (5) о балансе калорий.
Рецепты доступны на www.recipes.com [2].
    """,
]

print("🧹 Демонстрация очистки текста\n")
print("="*70)

for i, text in enumerate(example_texts, 1):
    print(f"\n📝 Пример {i} - ДО очистки:")
    print("-" * 70)
    print(text)
    
    cleaned = clean_text(text)
    print(f"\n✨ Пример {i} - ПОСЛЕ очистки:")
    print("-" * 70)
    print(cleaned)
    print("\n" + "="*70)

print("\n✅ Все артефакты успешно удалены!")
print("   - Ссылки (http, https, www)")
print("   - Цитаты в квадратных скобках [123]")
print("   - Цитаты в круглых скобках (123)")
print("   - Лишние пробелы")
