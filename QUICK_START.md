# Quick Start Guide - User Management System

## 🚀 Getting Started

### Installation
```bash
pip install -r requirements.txt
```

### First Time Setup
```bash
# 1. Start the bot (creates database automatically)
python bot.py

# 2. In another terminal, create first admin
python init_admin.py YOUR_TELEGRAM_ID "Your Name"

# 3. Find your Telegram ID
# Start a chat with @userinfobot on Telegram
```

## 📋 Admin Commands Reference

### View Admin Panel
```
/admin
```
Shows all available admin commands

### List All Users
```
/users
```
Shows: ID, Name, Role, Status, Registration Date

### Ban a User
```
/ban 123456789
```
Banned users cannot use the bot

### Unban a User
```
/unban 123456789
```
Restores user access

### Change User Role
```
/setrole 123456789 admin
/setrole 123456789 user
/setrole 123456789 guest
```
Roles: admin (full access), user (normal), guest (limited)

### View Logs
```
/logs                # All users, last 20 entries
/logs 123456789      # Specific user, last 20 entries
```

### Get User Info
```
/userinfo 123456789
```
Shows detailed user information

## 🗂️ Database Schema

### Users Table
| Field      | Type     | Description              |
|------------|----------|--------------------------|
| id         | INTEGER  | Telegram user ID (PK)    |
| name       | TEXT     | User's display name      |
| role       | TEXT     | admin / user / guest     |
| status     | TEXT     | active / banned          |
| created_at | DATETIME | Registration timestamp   |

### Logs Table
| Field     | Type     | Description           |
|-----------|----------|-----------------------|
| id        | INTEGER  | Auto-increment (PK)   |
| user_id   | INTEGER  | Telegram user ID      |
| action    | TEXT     | Action description    |
| timestamp | DATETIME | Action timestamp      |

## 🔍 Common Operations

### Check User Status
```python
from user_manager import user_manager

# Check if user is banned
is_banned = await user_manager.is_user_banned(user_id)

# Check if user is admin
is_admin = await user_manager.is_user_admin(user_id)
```

### Manual Database Query
```bash
# Using SQLite command line
sqlite3 bot_database.db

# View all users
SELECT * FROM users;

# View recent logs
SELECT * FROM logs ORDER BY timestamp DESC LIMIT 10;

# Count users by role
SELECT role, COUNT(*) FROM users GROUP BY role;
```

## 🛡️ Security Notes

1. **Database files are auto-excluded** from git
2. **Never commit** `bot_database.db` 
3. **First admin** must be created manually
4. **All inputs** are sanitized to prevent injection
5. **Admin actions** are logged with admin ID

## 📊 Monitoring

### View Activity
- Use `/logs` to see recent activity
- Check for suspicious patterns
- Review role changes regularly

### Database Backup
```bash
# Create backup
cp bot_database.db bot_database_backup_$(date +%Y%m%d).db

# Restore from backup
cp bot_database_backup_20260109.db bot_database.db
```

## 🔧 Troubleshooting

### Database not found
- Run bot once to create database
- Check current directory

### Cannot create admin
```bash
# Manual method
sqlite3 bot_database.db "UPDATE users SET role='admin' WHERE id=YOUR_ID;"
```

### View database schema
```bash
sqlite3 bot_database.db ".schema"
```

### Clear all data (WARNING: Destructive!)
```bash
rm bot_database.db
# Bot will recreate on next start
```

## 📚 Full Documentation

- **Database Details**: `DATABASE_DOCUMENTATION.md`
- **Implementation Info**: `IMPLEMENTATION_SUMMARY.md`
- **General Info**: `README.md`

## 🆘 Support

For issues or questions:
1. Check the documentation files
2. Review the logs: `/logs`
3. Check database with SQLite CLI
4. Review implementation summary

---
**Version**: 1.0  
**Last Updated**: 2026-01-09
