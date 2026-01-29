# Quick Start Guide - User Management

This guide helps you get started with the database-backed user management features of the AI Content Telegram Bot.

## Prerequisites

- Python 3.10+
- SQLite (included with Python)
- All requirements from `requirements.txt` installed

## Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

The user management features require:
- `sqlalchemy` - ORM for database operations
- `aiosqlite` - Async SQLite support
- `alembic` - Database migrations

These are already included in `requirements.txt`.

## Step 2: Initialize Database

The database is automatically initialized when you start the bot for the first time:

```bash
python bot.py
```

You'll see this log message:
```
✅ Database initialized successfully
```

The database file `bot_database.db` will be created in your project directory.

## Step 3: Create First Admin User

You need at least one admin user to manage the bot. There are three methods:

### Method A: Using init_admin.py (Recommended)

1. Find your Telegram user ID:
   - Start a chat with [@userinfobot](https://t.me/userinfobot) on Telegram
   - The bot will reply with your user ID

2. Run the init script:
   ```bash
   python init_admin.py <your_telegram_id> "Your Name"
   ```

   Example:
   ```bash
   python init_admin.py 123456789 "John Doe"
   ```

3. You'll see:
   ```
   Initializing database...
   
   Creating admin user:
     User ID: 123456789
     Name: John Doe
   
   ⚙️  Setting admin role...
   ✅ Admin user created successfully!
      You can now use admin commands in the bot.
   ```

### Method B: Using SQLite Command

If you prefer direct database access:

```bash
# First, start the bot once to create the database
python bot.py
# Stop it with Ctrl+C after you see "Database initialized"

# Then update the user to admin
sqlite3 bot_database.db "UPDATE users SET role='ADMIN' WHERE telegram_id=123456789;"
```

### Method C: Via Bot After First Use

1. Start the bot and send `/start` to register yourself
2. Stop the bot
3. Use Method B to promote yourself to admin
4. Restart the bot

## Step 4: Verify Admin Access

1. Start the bot
2. Send `/admin` to the bot
3. You should see the admin panel:

```
👑 Панель администратора

Доступные команды:
/users - Список всех пользователей
/ban <user_id> - Заблокировать пользователя
/unban <user_id> - Разблокировать пользователя
/setrole <user_id> <role> - Изменить роль (admin/user/guest)
/logs [user_id] - Просмотр логов
/userinfo <user_id> - Информация о пользователе
```

If you see "🚫 У вас нет прав администратора", check that:
- You used the correct Telegram user ID
- The database was updated successfully
- You restarted the bot after making changes

## Step 5: Common Admin Tasks

### List All Users
```
/users
```

### Get User Information
```
/userinfo 123456789
```

### Promote Another User to Admin
```
/setrole 987654321 admin
```

### Ban a User
```
/ban 987654321
```

### Unban a User
```
/unban 987654321
```

### View Audit Logs
```
/logs              # All logs
/logs 123456789    # Logs for specific user
```

## How It Works

### User Registration
- When a user sends `/start`, they are automatically registered
- Default role: `USER`
- Default status: `ACTIVE`
- User info (name, username) is updated on each interaction

### Ban System
- Banned users see: "🚫 Ваш аккаунт заблокирован"
- They cannot use any bot features
- Ban/unban actions are logged with admin attribution

### Role System
- **ADMIN**: Can use all admin commands
- **USER**: Can generate posts and use standard features
- **GUEST**: Limited access (customize as needed)

### Audit Logging
All important actions are logged:
- User registrations
- Role changes
- Ban/unban actions
- Post generation requests

View logs with `/logs` to monitor bot usage and security.

## Troubleshooting

### "Database initialization failed"
- Check file permissions in the project directory
- Ensure SQLite is properly installed
- Check disk space

### "User not found"
- User hasn't used `/start` yet
- Check the user ID is correct
- Verify database is initialized

### Admin commands not working
- Verify your role is 'ADMIN' in the database:
  ```bash
  sqlite3 bot_database.db "SELECT telegram_id, role FROM users WHERE telegram_id=YOUR_ID;"
  ```
- Restart the bot after role changes

### Database locked errors
- Ensure only one bot instance is running
- Close any SQLite browser connections

## Next Steps

1. **Read the full documentation**: See `DATABASE_DOCUMENTATION.md` for detailed information
2. **Set up backups**: Regularly backup `bot_database.db`
3. **Review logs**: Use `/logs` to monitor activity
4. **Customize roles**: Modify role permissions in `bot.py` as needed

## Security Tips

✅ **DO:**
- Backup your database regularly
- Keep admin access restricted to trusted users
- Review audit logs periodically
- Use the init_admin.py script for the first admin

❌ **DON'T:**
- Share your database file (contains user data)
- Grant admin role to unknown users
- Delete or modify logs manually
- Run multiple bot instances on the same database

## Support

For issues or questions:
1. Check `DATABASE_DOCUMENTATION.md` for detailed information
2. Review audit logs: `/logs`
3. Check bot logs in console output
4. Open an issue on GitHub with error details

---

**You're now ready to manage users and monitor your bot effectively!** 🚀
