# Pexels API Migration - Deployment Guide

## ✅ Migration Complete

The bot has been successfully migrated from Unsplash API to Pexels API for image generation.

## What Changed

### API Changes
- **Old**: Unsplash API (`UNSPLASH_API_KEY`)
- **New**: Pexels API (`PEXELS_API_KEY`)

### Rate Limits Improvement
- **Old**: 50 requests/hour (Unsplash free tier)
- **New**: 200 requests/hour (Pexels free tier)
- **Benefit**: 4x more capacity for image generation

### Code Changes
1. **image_fetcher.py**: Completely rewritten for Pexels API
   - New endpoint: `https://api.pexels.com/v1`
   - Different authentication header format
   - Different response structure
   - Enhanced error handling and logging

2. **bot.py**: Updated to use `PEXELS_API_KEY`
   - Changed all references from Unsplash to Pexels
   - Maintained backward compatibility with existing features

3. **Documentation**: All docs updated
   - README.md
   - FEATURES.md
   - IMPLEMENTATION_SUMMARY.md
   - .env.example

## Deployment Steps

### 1. Get Pexels API Key
1. Visit https://www.pexels.com/api/
2. Sign up for a free account
3. Create an API key (instant approval)
4. Copy your API key

### 2. Update Environment Variables

#### For Render.com:
1. Go to your Render dashboard
2. Select your service
3. Go to "Environment" tab
4. **Remove** old variable:
   - `UNSPLASH_API_KEY` (delete this)
5. **Add** new variable:
   - Key: `PEXELS_API_KEY`
   - Value: `your_pexels_api_key_here`
6. Save changes

#### For local development:
Update your `.env` file:
```bash
# Remove this line:
# UNSPLASH_API_KEY=...

# Add this line:
PEXELS_API_KEY=your_pexels_api_key_here
```

### 3. Deploy
- For Render: Code auto-deploys from GitHub
- For local: Restart the bot with `python bot.py`

### 4. Verify Deployment
Check the startup logs for:
```
🖼️ Pexels: ON
```

If you see this, the migration is successful!

## Testing

### Automated Tests
All tests pass:
- ✅ 8 unit tests for ImageFetcher
- ✅ Syntax validation
- ✅ Code review passed
- ✅ Security scan (CodeQL): 0 alerts

### Manual Testing Checklist
After deployment, test the following:

1. **Text-only posts** (should work as before):
   - Click "📝 Пост"
   - Enter a topic
   - Verify post is generated

2. **Posts with images** (new Pexels integration):
   - Click "🖼️ Пост с фото"
   - Enter a topic (e.g., "fitness", "business", "nature")
   - Verify:
     - ✅ Post text is generated
     - ✅ 3 images are fetched from Pexels
     - ✅ Images are relevant to the topic
     - ✅ Images are sent as a media group

3. **Error handling**:
   - Test with invalid/expired API key
   - Verify graceful fallback to text-only
   - Check logs for proper error messages

## Troubleshooting

### Images not showing up?
1. **Check API key**: Make sure `PEXELS_API_KEY` is set correctly
2. **Check logs**: Look for "Pexels API response status" messages
3. **Verify rate limit**: Pexels free tier = 200 requests/hour
4. **Test API key**: Use `test_pexels.py` script

### Common Error Messages

**"Pexels API key not configured"**
- Solution: Set `PEXELS_API_KEY` in environment variables

**"HTTP 401 Unauthorized"**
- Solution: Check if API key is valid and active

**"No images found"**
- This is normal for some queries
- Bot will fallback to text-only post
- Try a different topic

## Rollback Plan (if needed)

If you need to rollback to Unsplash:
1. Checkout previous commit before migration
2. Restore `UNSPLASH_API_KEY` environment variable
3. Redeploy

## Benefits Summary

✅ **Better rate limits**: 200 vs 50 requests/hour
✅ **More reliable**: Pexels has better uptime
✅ **Better image quality**: High-quality stock photos
✅ **Free forever**: No credit card required
✅ **Simple API**: Easier to work with
✅ **Good documentation**: Easy to debug

## Support

For issues or questions:
1. Check the logs first
2. Review this deployment guide
3. Check Pexels API status: https://www.pexels.com/api/
4. Open an issue on GitHub

---

**Status**: ✅ Ready for Production
**Last Updated**: 2026-01-11
**Version**: 2.2 (Pexels Migration)
