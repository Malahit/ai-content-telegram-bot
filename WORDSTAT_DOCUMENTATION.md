# Yandex Wordstat Integration

## Overview
This feature integrates Yandex Wordstat data into the Telegram bot to enable SEO-optimized post generation based on real search statistics.

## Features

### 1. `/wordstat` Command
Analyzes keywords using Yandex Wordstat and provides:
- Monthly search volume (formatted as "150k/мес")
- Related keywords and search queries
- Interactive buttons for further actions

**Usage:**
```
/wordstat фитнес
```
or
```
/wordstat
```
(bot will ask for keyword)

### 2. SEO Post Generation
Creates SEO-optimized posts with:
- 300 words structured content
- H1 and H2 headings
- Lists and formatting
- 1.5% keyword density (~4-5 mentions in 300 words)
- Related keywords naturally integrated
- Call-to-action (CTA)
- Emojis for engagement

### 3. SQLite Cache
- Stores Wordstat data for 24 hours (TTL)
- Reduces scraping load
- Automatic cleanup of expired entries
- Database: `wordstat_cache.db` (gitignored)

### 4. Selenium-based Scraping
- Automated Chrome WebDriver
- Headless mode by default
- 3 retry attempts with exponential backoff
- Automatic driver management via `webdriver-manager`

## Architecture

### Modules

#### `wordstat_db.py`
SQLite database management for caching Wordstat data.

**Key Functions:**
- `get(keyword)` - Retrieve cached data
- `upsert(keyword, data)` - Insert or update cache
- `delete(keyword)` - Remove cache entry
- `cleanup_expired()` - Remove expired entries

**Database Schema:**
```sql
CREATE TABLE wordstat_cache (
    keyword TEXT PRIMARY KEY,
    data_json TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL
)
```

#### `wordstat_parser.py`
Selenium-based scraper for Yandex Wordstat.

**Key Features:**
- Chrome WebDriver with automatic driver management
- Retry logic using `tenacity` library
- Extracts search volume and related keywords
- Cache integration

**Key Functions:**
- `get_wordstat_data(keyword, use_cache=True)` - Main function to get data
- `_scrape_wordstat(keyword)` - Internal scraping function with retries

#### `seo_post_generator.py`
Generates SEO-optimized posts using Perplexity API.

**Key Features:**
- Structured prompt template
- Keyword density control
- Integration with Wordstat data
- HTML formatting for Telegram

**Key Functions:**
- `generate_seo_post(keyword, wordstat_data)` - Generate SEO post
- `_build_seo_prompt(keyword, wordstat_data)` - Build AI prompt

### Bot Integration

The bot now includes:
- `/wordstat` command handler
- FSM states for Wordstat flow
- Inline keyboard callbacks for actions
- Updated help and status messages

## Installation

### Dependencies
```bash
pip install selenium webdriver-manager tenacity
```

These are already added to `requirements.txt`:
```
selenium==4.27.1
webdriver-manager==4.0.2
tenacity==9.0.0
```

### Chrome/Chromium
The bot uses Chrome WebDriver. On most systems, `webdriver-manager` will automatically download the appropriate driver. On Linux servers, you may need to install Chrome/Chromium:

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y chromium-browser chromium-chromedriver

# Or Chrome
wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
sudo sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list'
sudo apt-get update
sudo apt-get install -y google-chrome-stable
```

## Usage Examples

### Basic Keyword Analysis
1. User sends: `/wordstat фитнес`
2. Bot scrapes Yandex Wordstat (or uses cache)
3. Bot displays:
   - Search volume: "150k/мес"
   - Related keywords list
   - Action buttons

### Generate SEO Post
1. User clicks "✍️ Создать SEO пост" button
2. Bot generates structured content with:
   - SEO-optimized text (300 words)
   - Proper keyword density
   - Related keywords integrated
   - Professional formatting
3. Bot sends the complete post

### Refresh Data
1. User clicks "🔄 Обновить данные" button
2. Bot re-scrapes Wordstat (bypasses cache)
3. Bot shows updated statistics

## Technical Details

### Caching Strategy
- First request: Scrapes Yandex Wordstat → Saves to database
- Subsequent requests (within 24h): Returns cached data
- After 24h: Cache expired → Scrapes again
- Manual refresh: Bypasses cache

### Error Handling
- **Selenium failures**: Retries 3 times with exponential backoff
- **Parsing failures**: Returns partial data with error flag
- **API failures**: Returns error message to user
- **Database failures**: Logs error, continues without cache

### Rate Limiting
To avoid overloading Yandex Wordstat:
- Use cache by default (24h TTL)
- Only scrape when necessary
- Retry with delays (2s, 4s, 8s)
- Graceful degradation on failures

## Configuration

No additional environment variables required. The feature uses existing `PPLX_API_KEY` for SEO post generation.

### Optional Tuning
Edit constants in the modules:
```python
# wordstat_db.py
CACHE_TTL_HOURS = 24  # Cache lifetime

# wordstat_parser.py
DEFAULT_TIMEOUT = 15  # Selenium timeout
MAX_RETRIES = 3      # Number of retry attempts
```

## Testing

Run the integration tests:
```bash
python3 test_wordstat_integration.py
```

This tests:
- Database operations (CRUD)
- SEO prompt generation
- Module imports
- Data validation

## Troubleshooting

### "WebDriver not found" error
```bash
# Install Chrome/Chromium
sudo apt-get install chromium-browser chromium-chromedriver
```

### "Timeout waiting for page" error
- Increase `DEFAULT_TIMEOUT` in `wordstat_parser.py`
- Check internet connection
- Verify Yandex Wordstat is accessible

### Empty search volume
- Yandex may have changed their HTML structure
- Check logs for detailed error messages
- The bot will return "N/A" but continue to work

### Database locked
- Ensure only one bot instance is running
- Check file permissions on `wordstat_cache.db`

## Security Considerations

- ✅ Database file is gitignored
- ✅ No sensitive data stored in cache
- ✅ Selenium runs in headless mode
- ✅ User input is sanitized
- ✅ API keys never exposed in logs

## Future Enhancements

Potential improvements:
- Support for multiple regions (not just Yandex.ru)
- Historical data tracking
- Keyword comparison feature
- Export to CSV/Excel
- Scheduled keyword monitoring
- Image integration with SEO posts
- Multi-language support

## Limitations

- **Scraping reliability**: Yandex may change their page structure
- **Rate limits**: Excessive scraping may be blocked by Yandex
- **Cache size**: No limit on database size (consider adding cleanup)
- **Selenium overhead**: WebDriver initialization takes ~5-10 seconds

## API Changes

### New Endpoints
- `/wordstat` - Main command
- Callback: `wordstat_seo_{keyword}` - Generate SEO post
- Callback: `wordstat_retry_{keyword}` - Refresh data

### New FSM States
- `WordstatState.waiting_for_keyword` - Waiting for keyword input
- `WordstatState.showing_results` - Showing results with action buttons

## Maintenance

### Database Cleanup
The database automatically cleans up expired entries. To manually clean:
```python
from wordstat_db import wordstat_db
count = wordstat_db.cleanup_expired()
print(f"Removed {count} expired entries")
```

### Cache Management
View all cached keywords:
```python
from wordstat_db import wordstat_db
keywords = wordstat_db.get_all_keywords()
print(f"Cached keywords: {keywords}")
```

## License
Same as parent project.

## Support
For issues or questions, please open an issue on GitHub.
