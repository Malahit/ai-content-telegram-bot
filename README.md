# AI Content Telegram Bot

An advanced Telegram bot for generating AI-powered content with image integration, SEO optimization, and smart caching.

## Features

### 📝 Content Generation
- **Text Posts**: Generate high-quality text content (200-300 words) using Perplexity AI
- **Posts with Images**: Text content + up to 3 relevant images from multiple sources
- **SEO-Optimized Posts**: Use `/wordstat` command for keyword-focused content
- **RAG Integration**: Optional knowledge base integration for context-aware generation
- **Multi-language Support**: Automatic RU/EN translation

### 🖼️ Image Features
- **Multiple Image Sources**: Unsplash, Pexels, and Pixabay with automatic fallback
- **Smart Caching**: SQLite-based image cache with 48-hour TTL
- **Retry Logic**: Automatic retry with exponential backoff (3 attempts)
- **Rate Limiting**: Built-in rate limiting (5 requests/min) to prevent API bans
- **Error Handling**: Graceful fallback for 429/403 API responses

### 📊 Statistics & Monitoring
- **Usage Tracking**: Track post generation, active users, and popular topics
- **Admin Dashboard**: Statistics accessible to configured admin users
- **Comprehensive Logging**: Detailed logs for monitoring and troubleshooting

### ⏰ Automation
- **Auto-posting**: Scheduled posts every 6 hours to configured channel
- **Cache Cleanup**: Automatic cleanup of expired image cache

## Installation

### Prerequisites
- Python 3.8+
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))
- Perplexity API Key
- Optional: Unsplash/Pexels/Pixabay API keys for images

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/Malahit/ai-content-telegram-bot.git
   cd ai-content-telegram-bot
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   
   Copy `.env.example` to `.env` and fill in your credentials:
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env`:
   ```env
   # Required
   BOT_TOKEN=your_telegram_bot_token
   PPLX_API_KEY=your_perplexity_api_key
   CHANNEL_ID=@your_channel
   
   # Optional - Image APIs (with fallback)
   UNSPLASH_API_KEY=your_unsplash_api_key
   PEXELS_API_KEY=your_pexels_api_key
   PIXABAY_API_KEY=your_pixabay_api_key
   
   # Optional - Admin access
   ADMIN_USER_IDS=123456789,987654321
   ```

4. **Run the bot**
   ```bash
   python bot.py
   ```

## Usage

### Basic Commands

- `/start` - Start the bot and see available options
- `/wordstat` - Generate SEO-optimized post for a keyword

### Interactive Buttons

- **📝 Пост** - Generate text-only post
- **🖼️ Пост с фото** - Generate post with images
- **❓ Помощь** - Get help and usage instructions
- **ℹ️ Статус** - Check bot status and configuration
- **📊 Статистика** - View statistics (admin only)

### Examples

#### Text Post
1. Click "📝 Пост"
2. Enter topic: "SMM strategy for small business"
3. Receive generated content

#### Post with Images
1. Click "🖼️ Пост с фото"
2. Enter topic: "healthy breakfast ideas"
3. Receive content + 3 relevant images

#### SEO Post with Keyword
1. Send `/wordstat`
2. Enter keyword: "digital marketing"
3. Receive SEO-optimized content
4. Click "🖼️ Пост с фото" button to add image

## API Keys Setup

### Telegram Bot Token
1. Message [@BotFather](https://t.me/botfather)
2. Send `/newbot` and follow instructions
3. Copy the token to `BOT_TOKEN` in `.env`

### Perplexity API
1. Sign up at [Perplexity AI](https://www.perplexity.ai/)
2. Get your API key from dashboard
3. Add to `PPLX_API_KEY` in `.env`

### Image APIs (Optional)

**Unsplash** (Primary source)
1. Create account at [Unsplash Developers](https://unsplash.com/developers)
2. Create a new application
3. Copy access key to `UNSPLASH_API_KEY`
4. Free tier: 50 requests/hour

**Pexels** (Fallback)
1. Create account at [Pexels API](https://www.pexels.com/api/)
2. Get API key from dashboard
3. Add to `PEXELS_API_KEY`

**Pixabay** (Second fallback)
1. Create account at [Pixabay API](https://pixabay.com/api/docs/)
2. Get API key
3. Add to `PIXABAY_API_KEY`

> **Note**: At least one image API key is required for image features. The bot will automatically fall back to alternative sources if one fails.

### Finding Your Telegram User ID
Use [@userinfobot](https://t.me/userinfobot) or check bot logs when you send a message.

## Architecture

### Image Fetching
```
User Request
    ↓
Check Cache (48h TTL)
    ↓ (miss)
Try Unsplash (with retry)
    ↓ (fail)
Try Pexels
    ↓ (fail)
Try Pixabay
    ↓
Cache & Return
```

### Rate Limiting
- **5 requests per minute** to prevent API bans
- Automatic waiting when limit reached
- Per-session tracking

### Caching Strategy
- **Storage**: SQLite database (`image_cache.db`)
- **TTL**: 48 hours
- **Key**: Lowercase keyword
- **Auto-cleanup**: Expired entries removed on retrieval

## Testing

Run the test suite:
```bash
# All tests
python -m pytest tests/ -v

# Specific test file
python -m pytest tests/test_image_cache.py -v
python -m pytest tests/test_image_fetcher.py -v
```

### Test Coverage
- ✅ Image cache CRUD operations
- ✅ Cache expiration and cleanup
- ✅ Image fetching with retry logic
- ✅ Fallback chain (Unsplash → Pexels → Pixabay)
- ✅ Rate limiter functionality
- ✅ Error handling

## Configuration

### Optional Features

**RAG (Retrieval-Augmented Generation)**
- Place documents in `knowledge/` folder
- Bot will use them as context for generation
- Automatically detected if dependencies installed

**Translation**
- Automatic RU/EN translation
- Requires `langdetect` and `deep-translator`
- Automatically enabled if dependencies installed

## File Structure

```
.
├── bot.py                  # Main bot application
├── image_fetcher.py        # Image fetching with retry & fallback
├── image_cache_db.py       # SQLite image cache
├── bot_statistics.py       # Statistics tracking
├── rag/                    # RAG module (optional)
├── tests/                  # Test suite
│   ├── test_image_cache.py
│   └── test_image_fetcher.py
├── requirements.txt        # Python dependencies
├── .env.example           # Environment template
└── README.md              # This file
```

## Troubleshooting

### Images not showing
- ✅ Verify at least one image API key is configured
- ✅ Check API key is valid and not expired
- ✅ Check bot logs for specific error messages
- ✅ Verify API rate limits not exceeded

### Statistics button not visible
- ✅ Add your Telegram user ID to `ADMIN_USER_IDS` in `.env`
- ✅ Restart the bot
- ✅ Send `/start` to refresh keyboard

### Rate limit errors
- ✅ Wait for rate limit period to expire
- ✅ Add additional API keys (Pexels, Pixabay) for fallback
- ✅ Reduce usage frequency

### Cache issues
- ✅ Check `image_cache.db` file permissions
- ✅ Delete `image_cache.db` to reset cache
- ✅ Check disk space

## API Rate Limits

| Service | Free Tier | Notes |
|---------|-----------|-------|
| Unsplash | 50 req/hour | Primary source |
| Pexels | 200 req/hour | First fallback |
| Pixabay | 5000 req/hour | Second fallback |
| Perplexity | Varies by plan | Content generation |

## Security

- ✅ API keys stored in `.env` (gitignored)
- ✅ Admin IDs configurable via environment
- ✅ Statistics file excluded from git
- ✅ No sensitive data in logs
- ✅ Minimal user data collection
- ✅ **aiohttp 3.13.3** - Patched version (fixes CVE vulnerabilities)

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new features
4. Ensure all tests pass
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

For issues or questions:
- Open an issue on GitHub
- Check logs for error details
- Review this README

## Changelog

### v2.2 (Current)
- ✨ Added `/wordstat` command for SEO posts
- ✨ Image caching with SQLite
- ✨ Multi-source image fetching (Unsplash, Pexels, Pixabay)
- ✨ Retry logic with tenacity
- ✨ Rate limiting for API calls
- ✨ Async image fetching with aiohttp
- ✨ Comprehensive test suite
- 🐛 Fixed image API error handling
- 📝 Improved documentation

### v2.1
- ✨ Posts with images feature
- ✨ Statistics tracking
- ✨ Admin dashboard
- ✨ RAG integration
- ✨ Auto-posting

### v2.0
- Initial release with basic post generation
