# Yandex Wordstat Integration - Quick Start Guide

## What is this feature?

The Yandex Wordstat integration allows you to:
1. Analyze keyword popularity using real Yandex search data
2. Generate SEO-optimized posts based on that data
3. All through simple Telegram bot commands

## Quick Examples

### Example 1: Analyze a keyword
```
User: /wordstat фитнес

Bot: 📊 Yandex Wordstat - Результаты

🔑 Ключевое слово: фитнес
📈 Запросов в месяц: 150k/мес

🔗 Связанные запросы (8):
1. фитнес дома
2. фитнес упражнения
3. фитнес питание
4. фитнес зал
5. фитнес тренер
...

[✍️ Создать SEO пост] [🔄 Обновить данные]
```

### Example 2: Generate SEO post
After clicking "✍️ Создать SEO пост":

```
Bot: # 💪 Фитнес: Путь к здоровью и энергии

Современный фитнес — это не просто тренировки, это образ жизни...

## Почему фитнес важен?

Фитнес приносит множество преимуществ:
• Улучшает физическую форму
• Повышает энергию
• Помогает контролировать вес
...

📊 SEO данные:
🔍 Запросов: 150k/мес
🔗 Связанных тем: 8
```

## Installation

### For Users
No setup needed! Just use the bot commands.

### For Developers/Deployment

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Install Chrome (if needed):**
```bash
# Ubuntu/Debian
sudo apt-get install chromium-browser

# Or let webdriver-manager handle it automatically
```

3. **Run the bot:**
```bash
python3 bot.py
```

That's it! No additional API keys or configuration needed.

## Usage

### Command Syntax
```
/wordstat [keyword]
```

**Examples:**
- `/wordstat фитнес`
- `/wordstat SMM`
- `/wordstat недвижимость`
- `/wordstat` (bot will ask for keyword)

### Workflow

```
┌─────────────────────┐
│ User sends          │
│ /wordstat fitness   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Check Cache         │
│ (24-hour TTL)       │
└──────────┬──────────┘
           │
     ┌─────┴─────┐
     │           │
  Hit│           │Miss
     │           │
     ▼           ▼
┌─────────┐  ┌──────────────┐
│ Return  │  │ Scrape Yandex│
│ Cached  │  │ Wordstat     │
│ Data    │  └──────┬───────┘
└────┬────┘         │
     │              │
     │    ┌─────────┘
     │    │
     ▼    ▼
┌────────────────────┐
│ Display Results    │
│ + Action Buttons   │
└──────────┬─────────┘
           │
    ┌──────┴──────┐
    │             │
    ▼             ▼
┌────────┐  ┌──────────┐
│Generate│  │ Refresh  │
│SEO Post│  │   Data   │
└────────┘  └──────────┘
```

## Features

### 1. Smart Caching
- First request: Scrapes Yandex (~15-30 seconds)
- Subsequent requests: Instant response from cache
- Cache expires after 24 hours
- Manual refresh available via button

### 2. SEO Post Structure
Generated posts include:
- **H1 heading** with main keyword
- **H2 subheadings** (2-3) for structure
- **Lists** for easy reading
- **Emojis** for engagement
- **HTML formatting** for Telegram
- **1.5% keyword density** (SEO optimized)
- **Related keywords** naturally integrated
- **Call-to-action** at the end

### 3. Error Handling
- Graceful fallback on scraping failures
- Clear error messages
- Partial data returned when possible
- Automatic retries (3 attempts)

## Common Use Cases

### For Content Creators
1. Research trending topics
2. Generate SEO-optimized posts
3. Find related keywords for content ideas

### For Marketers
1. Analyze keyword popularity
2. Create data-driven content
3. Track search trends

### For Bloggers
1. Find popular topics in your niche
2. Optimize post keywords
3. Generate structured content quickly

## Troubleshooting

### "WebDriver not found"
```bash
sudo apt-get install chromium-browser
```

### "No data found"
- Keyword may not have enough search volume
- Try a more popular keyword
- Check if Yandex Wordstat is accessible in your region

### "Timeout error"
- Yandex may be slow to respond
- Bot will retry automatically (3 times)
- Try again later or use cached data

### Cache issues
```bash
# Clear cache if needed
rm wordstat_cache.db
```

## Tips for Best Results

1. **Use Russian keywords** - Yandex Wordstat is for Russian search market
2. **Be specific** - "фитнес дома" better than just "фитнес"
3. **Check related keywords** - Often more valuable than main keyword
4. **Use cache wisely** - Data doesn't change much daily
5. **Generate SEO posts** - Make use of the structured content

## Limitations

- **Language:** Best with Russian keywords (Yandex.ru)
- **Region:** Yandex Wordstat may not be accessible in some regions
- **Scraping:** Depends on Yandex page structure (may break if they change it)
- **Speed:** First request takes 15-30 seconds (scraping time)

## Support

For issues or questions:
1. Check `WORDSTAT_DOCUMENTATION.md` for technical details
2. Review `FEATURES.md` for feature overview
3. Open an issue on GitHub

## Version History

- **v2.3** (Jan 2026) - Initial Wordstat integration
  - Keyword analysis
  - SEO post generation
  - Smart caching
  - Retry logic

---

**Made with ❤️ for better content creation**
