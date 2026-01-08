# Quick Start Guide - User Management

This guide will help you set up and use the user management system in under 5 minutes.

## Prerequisites

- Python 3.7+
- Telegram Bot Token
- Perplexity API Key

## Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

## Step 2: Configure Environment

Copy the example environment file and fill in your values:

```bash
cp .env.example .env
```

Edit `.env` and set:
- `BOT_TOKEN` - Your Telegram bot token from @BotFather
- `PPLX_API_KEY` - Your Perplexity API key
- `CHANNEL_ID` - Your Telegram channel ID (optional)
- `ADMIN_IDS` - Your Telegram user ID(s), comma-separated

**How to find your Telegram ID:**
1. Message @userinfobot on Telegram
2. Copy the ID number it gives you
3. Add it to `ADMIN_IDS` in `.env`

Example `.env`:
```bash
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
PPLX_API_KEY=pplx-abc123def456
CHANNEL_ID=@my_channel
ADMIN_IDS=123456789
```

## Step 3: Initialize Database (Optional)

The database initializes automatically when you start the bot, but you can do it manually:

```bash
# Initialize database
python setup_db.py init

# Create an admin user (optional - can also be done via .env)
python setup_db.py create_admin YOUR_TELEGRAM_ID "Your Name"

# View all users
python setup_db.py list
```

## Step 4: Start the Bot

```bash
python bot.py
```

You should see:
```
✅ Database initialized
✅ BOT v2.1 PRODUCTION READY!
```

## Step 5: Use the Bot

### As a Regular User

1. Start the bot in Telegram: `/start`
2. Register: `/register`
3. Request permission from admin if needed

### As an Admin

All regular user commands plus:

```
/list_users                  # View all users
/ban 987654321              # Ban a user by ID
/unban 987654321            # Unban a user
/set_role 987654321 user    # Change user role
```

## Common Commands

| Command | Description | Who Can Use |
|---------|-------------|-------------|
| `/start` | Start the bot | Everyone |
| `/register` | Register or view your info | Everyone |
| `/help` | Get help (role-specific) | Everyone |
| `/list_users` | List all users | Admin only |
| `/ban <user_id>` | Ban a user | Admin only |
| `/unban <user_id>` | Unban a user | Admin only |
| `/set_role <user_id> <role>` | Change user role | Admin only |

## User Roles

| Role | Permissions |
|------|-------------|
| **Guest** | View help and status only |
| **User** | Generate content + all guest permissions |
| **Admin** | Everything + user management |

## Example Workflow

1. **User joins bot:**
   - User: `/start` → Auto-registered as "guest"
   - User: `/register` → Sees their guest status
   
2. **Admin grants access:**
   - Admin: `/list_users` → Sees new user
   - Admin: `/set_role 987654321 user` → Upgrades user
   
3. **User generates content:**
   - User can now generate AI content
   
4. **Handle problem user:**
   - Admin: `/ban 987654321` → User is blocked

## Troubleshooting

**"Database not found" error:**
- The database creates automatically on first run
- Check write permissions in the bot directory

**"Insufficient permissions" error:**
- Make sure your Telegram ID is in `ADMIN_IDS` in `.env`
- Restart the bot after changing `.env`

**Can't find my Telegram ID:**
- Message @userinfobot on Telegram
- It will reply with your user ID

**Bot doesn't respond:**
- Check BOT_TOKEN is correct
- Verify bot is running (`python bot.py`)
- Check bot logs for errors

## Next Steps

- Read [USER_MANAGEMENT.md](USER_MANAGEMENT.md) for detailed documentation
- See [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) for technical details
- Run tests: `python test_user_management.py`

## Support

For issues or questions, check the documentation or contact your bot administrator.
