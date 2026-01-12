# New Features Documentation

## Overview
This document describes the new features added to the AI Content Telegram Bot v2.2.

## 1. Post Types

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
- Images are automatically fetched from Pexels based on your topic
- Images are sent as a media group with the text as caption

**How to use:**
1. Click the "🖼️ Пост с фото" button
2. Enter your topic
3. Receive generated text content with relevant images

**Requirements:**
- Requires `PEXELS_API_KEY` in `.env` file
- Get your free API key at: https://www.pexels.com/api/

**Error Handling:**
- If images cannot be fetched (API error, no results), the bot falls back to text-only
- Clear error messages are shown to the user

## 2. Statistics Feature (Admin Only)

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

## 3. Configuration

### Required Environment Variables:
```bash
BOT_TOKEN=your_telegram_bot_token
PPLX_API_KEY=your_perplexity_api_key
CHANNEL_ID=@your_channel
```

### Optional Environment Variables:
```bash
# For posts with images feature
PEXELS_API_KEY=your_pexels_api_key

# For admin access to statistics
ADMIN_USER_IDS=123456789,987654321
```

See `.env.example` for a complete template.

## 4. User Interface Updates

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

## 5. Logging

All new features include comprehensive logging:

- **Statistics:** Every post generation is logged
- **Images:** Image fetch attempts and results are logged
- **Errors:** All errors are logged with details
- **Admin Access:** Admin-only feature access is logged

Check logs to monitor bot usage and troubleshoot issues.

## 6. Error Handling

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

## 7. Future Enhancements

Potential improvements for future versions:

- Export statistics to CSV/Excel
- More detailed analytics (time-based trends)
- Image selection/customization options
- Additional image sources (Pixabay, Unsplash)
- User-specific statistics
- Scheduled posts with images

## 8. Troubleshooting

### Images not showing:
- ✅ Check `PEXELS_API_KEY` is set correctly
- ✅ Verify your Pexels API key is active
- ✅ Check bot logs for error messages
- ✅ Ensure you haven't exceeded the rate limit (200 requests/hour)

### Statistics button not visible:
- ✅ Verify your Telegram user ID is in `ADMIN_USER_IDS`
- ✅ Restart the bot after changing `.env`
- ✅ Send `/start` command to refresh keyboard

### Statistics not updating:
- ✅ Check file permissions for `bot_statistics.json`
- ✅ Check logs for errors
- ✅ Verify the file is not corrupted

## 9. API Rate Limits

### Pexels API:
- **Free Tier:** 200 requests/hour
- **Recommendation:** Monitor usage in production
- **Fallback:** Bot automatically handles API failures
- **Documentation:** https://www.pexels.com/api/documentation/

### Perplexity API:
- Unchanged from previous version
- Rate limits depend on your plan

## 10. Security Considerations

- ✅ Admin user IDs are stored in `.env` (not in code)
- ✅ Statistics file is gitignored (not committed to repo)
- ✅ API keys are never logged or exposed
- ✅ User data is minimal (only user IDs tracked)
- ✅ No personally identifiable information stored

---

For questions or issues, check the main README or open an issue on GitHub.
