# New Features Documentation

## Overview
This document describes the features of the AI Content Telegram Bot v2.3.

## 1. Yandex Wordstat Integration (NEW in v2.3)

### 📊 SEO-Optimized Post Generation
The bot now integrates with Yandex Wordstat to create SEO-optimized content based on real search statistics.

**Features:**
- Keyword analysis with monthly search volume
- Related keywords discovery
- SEO post generation (300 words, structured with H1/H2, 1.5% keyword density)
- Smart caching (24-hour TTL)
- Retry mechanism for reliability

**How to use:**
1. Send `/wordstat [keyword]` (e.g., `/wordstat фитнес`)
2. View search statistics and related keywords
3. Click "✍️ Создать SEO пост" to generate optimized content
4. Click "🔄 Обновить данные" to refresh statistics

**Technical Details:**
- Uses Selenium WebDriver for scraping Yandex Wordstat
- SQLite cache with automatic expiration
- Integration with Perplexity API for content generation
- See `WORDSTAT_DOCUMENTATION.md` for complete documentation

**Requirements:**
- Selenium, webdriver-manager, tenacity (included in requirements.txt)
- Chrome/Chromium browser (auto-installed by webdriver-manager)

## 2. Post Types

The bot now supports two types of posts:

### 📝 Text-Only Posts
- Generates high-quality text content (200-300 words)
- Includes emojis and structured formatting
- Perfect for quick content creation

**How to use:**
1. Click the "📝 Пост" button
2. Enter your topic
3. Receive generated text content

### 🖼️ Posts with Images
- Generates text content PLUS up to 3 relevant images
- Images are automatically fetched from Unsplash based on your topic
- Images are sent as a media group with the text as caption

**How to use:**
1. Click the "🖼️ Пост с фото" button
2. Enter your topic
3. Receive generated text content with relevant images

**Requirements:**
- Requires `UNSPLASH_API_KEY` in `.env` file
- Get your free API key at: https://unsplash.com/developers

**Error Handling:**
- If images cannot be fetched (API error, no results), the bot falls back to text-only
- Clear error messages are shown to the user

## 3. Statistics Feature (Admin Only)

Track bot usage and popular content topics.

### 📊 Statistics Button
- **Access:** Only visible to admin users (configured via `ADMIN_USER_IDS`)
- **Location:** Bottom of the keyboard (only for admins)

### What Statistics Track:
1. **Total Posts Generated**
   - Overall count
   - Split by type (text-only vs. with images)

2. **Active Users**
   - Count of unique users who have generated posts

3. **Popular Topics**
   - Most frequently requested topics
   - Shows top 5 topics with their counts

### How to Access Statistics:
1. Configure your Telegram user ID in `.env`:
   ```
   ADMIN_USER_IDS=123456789,987654321
   ```
2. Restart the bot
3. The "📊 Статистика" button will appear in your keyboard
4. Click it to view the statistics report

**Finding your Telegram User ID:**
- Use bots like @userinfobot
- Or check the bot logs when you send a message

### Data Storage:
- Statistics are stored in `bot_statistics.json` (gitignored)
- File is created automatically on first use
- Data persists across bot restarts

## 4. Configuration

### Required Environment Variables:
```bash
BOT_TOKEN=your_telegram_bot_token
PPLX_API_KEY=your_perplexity_api_key
CHANNEL_ID=@your_channel
```

### Optional Environment Variables:
```bash
# For posts with images feature
UNSPLASH_API_KEY=your_unsplash_api_key

# For admin access to statistics
ADMIN_USER_IDS=123456789,987654321
```

**Note:** Yandex Wordstat feature works without additional API keys. It uses Selenium for scraping and the existing `PPLX_API_KEY` for SEO post generation.

See `.env.example` for a complete template.

## 5. User Interface Updates

### Updated Keyboard Layout:

**Regular Users:**
```
┌──────────────┬──────────────────┐
│  📝 Пост     │  🖼️ Пост с фото  │
├──────────────┼──────────────────┤
│  ❓ Помощь   │  ℹ️ Статус       │
└──────────────┴──────────────────┘
```

**Admin Users:**
```
┌──────────────┬──────────────────┐
│  📝 Пост     │  🖼️ Пост с фото  │
├──────────────┼──────────────────┤
│  ❓ Помощь   │  ℹ️ Статус       │
├──────────────┴──────────────────┤
│        📊 Статистика            │
└─────────────────────────────────┘
```

## 6. Logging

All new features include comprehensive logging:

- **Statistics:** Every post generation is logged
- **Images:** Image fetch attempts and results are logged
- **Errors:** All errors are logged with details
- **Admin Access:** Admin-only feature access is logged

Check logs to monitor bot usage and troubleshoot issues.

## 7. Error Handling

The implementation includes robust error handling:

1. **Image API Failures:**
   - Graceful fallback to text-only posts
   - User-friendly error messages
   - Automatic retry not implemented (to avoid rate limits)

2. **Statistics Errors:**
   - File I/O errors are caught and logged
   - Default statistics created if file is corrupted
   - No impact on core bot functionality

3. **Admin Access:**
   - Non-admin users get clear "Access Denied" message
   - Statistics button not shown to non-admins

## 8. Future Enhancements

Potential improvements for future versions:

- Export statistics to CSV/Excel
- More detailed analytics (time-based trends)
- Image selection/customization options
- Multiple image sources (Pexels, Pixabay)
- User-specific statistics
- Scheduled posts with images
- **Wordstat enhancements:**
  - Historical keyword tracking
  - Keyword comparison feature
  - Regional Wordstat data (beyond Yandex.ru)
  - Automatic SEO reports
  - Integration with Google Analytics

## 9. Troubleshooting

### Images not showing:
- ✅ Check `UNSPLASH_API_KEY` is set correctly
- ✅ Verify your Unsplash API key is active
- ✅ Check bot logs for error messages

### Statistics button not visible:
- ✅ Verify your Telegram user ID is in `ADMIN_USER_IDS`
- ✅ Restart the bot after changing `.env`
- ✅ Send `/start` command to refresh keyboard

### Statistics not updating:
- ✅ Check file permissions for `bot_statistics.json`
- ✅ Check logs for errors
- ✅ Verify the file is not corrupted

### Wordstat not working:
- ✅ Install Chrome/Chromium: `sudo apt-get install chromium-browser`
- ✅ Check internet connection to wordstat.yandex.ru
- ✅ Verify Selenium dependencies are installed
- ✅ Check logs for detailed error messages
- ✅ Try clearing cache: delete `wordstat_cache.db`

### Wordstat returns "N/A":
- ✅ Yandex may have changed their page structure
- ✅ Try a different keyword
- ✅ Check if Yandex Wordstat website is accessible in your region

## 10. API Rate Limits

### Unsplash API:
- **Free Tier:** 50 requests/hour
- **Recommendation:** Monitor usage in production
- **Fallback:** Bot automatically handles API failures

### Perplexity API:
- Used for both regular posts and SEO posts
- Rate limits depend on your plan
- Wordstat SEO posts may use slightly more tokens (~1000 vs 800)

### Yandex Wordstat:
- **No official API** - uses web scraping
- **24-hour cache** to minimize requests
- **Retry logic** with exponential backoff
- **Recommendation:** Don't abuse the scraping (respects Yandex's resources)

## 11. Security Considerations

- ✅ Admin user IDs are stored in `.env` (not in code)
- ✅ Statistics file is gitignored (not committed to repo)
- ✅ Wordstat cache database is gitignored
- ✅ API keys are never logged or exposed
- ✅ User data is minimal (only user IDs tracked)
- ✅ No personally identifiable information stored
- ✅ Selenium runs in headless mode (no GUI exposure)
- ✅ Web scraping is done responsibly with caching

---

For questions or issues, check the main README or open an issue on GitHub.
