# Database and User Management Documentation

## Overview

This bot now includes a robust database system for user management and audit logging using SQLAlchemy with SQLite.

## Database Schema

### Users Table
Stores information about all bot users.

| Field | Type | Description |
|-------|------|-------------|
| `id` | INTEGER (PRIMARY KEY) | Telegram user ID (unique) |
| `name` | TEXT | User's display name in Telegram |
| `role` | TEXT | User role: `admin`, `user`, or `guest` |
| `status` | TEXT | User status: `active` or `banned` |
| `created_at` | DATETIME | Timestamp when user was added |

### Logs Table
Stores audit trail of user actions.

| Field | Type | Description |
|-------|------|-------------|
| `id` | INTEGER (PRIMARY KEY, AUTO-INCREMENT) | Unique log entry ID |
| `user_id` | INTEGER | Telegram user ID associated with the action |
| `action` | TEXT | Description of the action performed |
| `timestamp` | DATETIME | Timestamp when action occurred |

## Features

### Automatic User Registration
- New users are automatically registered when they first use `/start`
- Default role: `user`
- Default status: `active`
- User registration is logged in the audit trail

### User Ban System
- Banned users cannot use the bot
- Ban status is checked before processing user requests
- Ban/unban actions are logged

### Role-Based Access Control
- **admin**: Full access to admin commands
- **user**: Standard bot functionality
- **guest**: Limited access (can be customized)

### Audit Logging
The following events are automatically logged:
- User registration
- Role changes (with admin ID if applicable)
- Account status updates (ban/unban with admin ID)
- Post generation requests

## Admin Commands

All admin commands require the user to have `admin` role.

### `/admin`
Display the admin panel with available commands.

**Example:**
```
/admin
```

### `/users`
List all registered users with their details.

**Example:**
```
/users
```

**Output:**
```
👥 Список пользователей:

✅ 👤 John Doe
  ID: 12345
  Роль: user | Статус: active
  Создан: 2026-01-09 10:30

✅ 👨‍💼 Admin User
  ID: 99999
  Роль: admin | Статус: active
  Создан: 2026-01-09 09:00
```

### `/ban <user_id>`
Ban a user by their Telegram ID.

**Example:**
```
/ban 12345
```

**Notes:**
- Admins cannot ban themselves
- Action is logged with admin ID

### `/unban <user_id>`
Unban a previously banned user.

**Example:**
```
/unban 12345
```

### `/setrole <user_id> <role>`
Change a user's role.

**Available roles:** `admin`, `user`, `guest`

**Example:**
```
/setrole 12345 admin
```

**Notes:**
- Action is logged with admin ID

### `/logs [user_id]`
View audit logs.

**Examples:**
```
/logs           # View last 20 logs for all users
/logs 12345     # View last 20 logs for user 12345
```

**Output:**
```
📝 Логи пользователя 12345:

🕒 2026-01-09 10:45:30
👤 User: 12345
📄 Generated post: 'Python tutorial'

🕒 2026-01-09 10:30:15
👤 User: 12345
📄 User registered: name='John Doe', role='user'
```

### `/userinfo <user_id>`
Get detailed information about a specific user.

**Example:**
```
/userinfo 12345
```

**Output:**
```
👤 Информация о пользователе:

✅ 👤 John Doe

ID: 12345
Роль: user
Статус: active
Создан: 2026-01-09 10:30:15
```

## Database Module (`database.py`)

### Initialization
```python
from database import db

# Initialize database (called automatically on bot startup)
await db.init_db()
```

### User Operations
```python
# Add a user
user = await db.add_user(user_id=12345, name="John Doe", role="user", status="active")

# Get a user
user = await db.get_user(user_id=12345)

# Update user role
success = await db.update_user_role(user_id=12345, role="admin")

# Update user status
success = await db.update_user_status(user_id=12345, status="banned")

# Get all users
users = await db.get_all_users()
```

### Logging Operations
```python
# Add a log entry
log = await db.add_log(user_id=12345, action="Generated post about Python")

# Get logs for a specific user
logs = await db.get_user_logs(user_id=12345, limit=100)

# Get all logs
logs = await db.get_all_logs(limit=100)
```

## User Manager Module (`user_manager.py`)

### User Registration
```python
from user_manager import user_manager

# Register a new user (automatically logs the action)
success = await user_manager.register_user(
    user_id=12345,
    name="John Doe",
    role="user"
)
```

### Role Management
```python
# Change user role (automatically logs the action)
success = await user_manager.change_role(
    user_id=12345,
    new_role="admin",
    admin_id=99999  # Optional: ID of admin performing the action
)
```

### Status Management
```python
# Ban a user (automatically logs the action)
success = await user_manager.ban_user(
    user_id=12345,
    admin_id=99999  # Optional
)

# Unban a user (automatically logs the action)
success = await user_manager.unban_user(
    user_id=12345,
    admin_id=99999  # Optional
)

# Check if user is banned
is_banned = await user_manager.is_user_banned(user_id=12345)

# Check if user is admin
is_admin = await user_manager.is_user_admin(user_id=12345)
```

### User Information
```python
# Get user information as dictionary
user_info = await user_manager.get_user_info(user_id=12345)
# Returns: {'id': 12345, 'name': 'John Doe', 'role': 'user', 'status': 'active', 'created_at': datetime}
```

## Database Connection

### Configuration
By default, the bot uses SQLite with the database file `bot_database.db` in the bot directory.

To use PostgreSQL instead:
```python
from database import Database

db = Database(db_url="postgresql+asyncpg://user:password@localhost/botdb")
await db.init_db()
```

### Connection Pooling
The database module includes:
- Connection pool with pre-ping verification
- Automatic connection recycling (1 hour)
- Exception handling for all operations
- Async session management

### Cleanup
```python
# Close database connection (called automatically on bot shutdown)
await db.close()
```

## Security Considerations

1. **Database files are excluded from git** via `.gitignore`
2. **Role-based access control** ensures only admins can manage users
3. **Audit logging** tracks all administrative actions
4. **Input validation** on all admin commands
5. **SQL injection protection** via SQLAlchemy ORM

## Creating the First Admin

To create the first admin user, you need to:

1. Start the bot and use `/start` command to register
2. Manually update the database:
```bash
sqlite3 bot_database.db "UPDATE users SET role='admin' WHERE id=YOUR_TELEGRAM_ID;"
```

Or programmatically:
```python
await db.update_user_role(user_id=YOUR_TELEGRAM_ID, role='admin')
```

## Troubleshooting

### Database not initializing
- Check file permissions in the bot directory
- Verify SQLAlchemy and aiosqlite are installed
- Check logs for detailed error messages

### User not being registered
- Ensure database is initialized before bot starts
- Check logs for database errors
- Verify user_id is valid Telegram ID

### Admin commands not working
- Verify your user role is 'admin' in database
- Check that you're using correct command syntax
- Review logs for permission errors

## Performance Notes

- SQLite is suitable for small to medium deployments (< 1000 users)
- For larger deployments, consider PostgreSQL
- Logs table will grow over time - consider periodic cleanup
- Database file is typically small (< 1MB for hundreds of users)
