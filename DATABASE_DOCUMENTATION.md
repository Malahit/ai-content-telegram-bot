# Database and User Management Documentation

## Overview

The AI Content Telegram Bot now includes a comprehensive database system for user management and audit logging using SQLAlchemy with SQLite. This implementation integrates seamlessly with the existing subscription and payment system.

## Database Schema

### Users Table
Stores comprehensive information about all bot users, including subscription status and access control.

| Field | Type | Description |
|-------|------|-------------|
| `id` | INTEGER (PRIMARY KEY) | Auto-increment database ID |
| `telegram_id` | BIGINT (UNIQUE) | Telegram user ID (indexed) |
| `username` | VARCHAR(255) | User's Telegram username (optional) |
| `first_name` | VARCHAR(255) | User's first name (optional) |
| `last_name` | VARCHAR(255) | User's last name (optional) |
| `is_premium` | BOOLEAN | Premium subscription status |
| `subscription_end` | DATETIME | Subscription expiration date (optional) |
| `role` | ENUM | User role: `ADMIN`, `USER`, or `GUEST` |
| `status` | ENUM | User status: `ACTIVE` or `BANNED` |
| `created_at` | DATETIME | Timestamp when user was registered |
| `updated_at` | DATETIME | Timestamp of last update |

### Logs Table
Stores audit trail of user actions for compliance and monitoring.

| Field | Type | Description |
|-------|------|-------------|
| `id` | INTEGER (PRIMARY KEY) | Auto-increment log entry ID |
| `user_id` | BIGINT | Telegram user ID (indexed) |
| `action` | VARCHAR(500) | Description of the action performed |
| `timestamp` | DATETIME | Timestamp when action occurred (indexed) |

### Payments Table
Tracks subscription payments and transactions.

| Field | Type | Description |
|-------|------|-------------|
| `id` | INTEGER (PRIMARY KEY) | Auto-increment payment ID |
| `user_id` | BIGINT | Telegram user ID (indexed) |
| `amount` | INTEGER | Payment amount |
| `currency` | VARCHAR(10) | Currency code |
| `status` | ENUM | Payment status: `PENDING`, `SUCCESS`, or `FAILED` |
| `provider` | VARCHAR(50) | Payment provider name |
| `payload` | JSON | Additional payment data (optional) |
| `paid_at` | DATETIME | Payment completion timestamp (optional) |
| `created_at` | DATETIME | Payment creation timestamp |

## Features

### Automatic User Registration
- New users are automatically registered when they first use `/start`
- Default role: `USER`
- Default status: `ACTIVE`
- User information (username, first_name, last_name) is updated on each interaction
- User registration is logged in the audit trail

### User Ban System
- Banned users cannot use the bot
- Ban status is checked before processing user requests
- Ban/unban actions are logged with admin attribution
- Admins cannot ban themselves

### Role-Based Access Control
- **ADMIN**: Full access to all admin commands and bot features
- **USER**: Standard bot functionality (post generation, images)
- **GUEST**: Limited access (can be customized for restricted users)

### Audit Logging
The following events are automatically logged with sanitized input:
- User registration
- Role changes (with admin ID attribution)
- Account status updates (ban/unban with admin ID attribution)
- Post generation requests (topic and type)

### Security Features
- **Input Sanitization**: All user input is sanitized before logging to prevent log injection attacks
  - Newlines and carriage returns are replaced with spaces
  - Maximum length limit (200 characters) to prevent log flooding
- **SQL Injection Prevention**: SQLAlchemy ORM prevents SQL injection attacks
- **Access Control**: Admin commands are protected by role verification

## Admin Commands

All admin commands require the user to have `ADMIN` role.

### `/admin`
Display the admin panel with available commands.

**Example:**
```
/admin
```

**Output:**
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

### `/users`
List all registered users with their details (up to 50 users).

**Example:**
```
/users
```

**Output:**
```
👥 Список пользователей:

👑 ✅ Admin User
   ID: 123456789 | Role: ADMIN | Status: ACTIVE

👤 ✅ John Doe
   ID: 987654321 | Role: USER | Status: ACTIVE

👤 🚫 Jane Smith
   ID: 555555555 | Role: USER | Status: BANNED
```

### `/ban <user_id>`
Ban a user by their Telegram ID.

**Example:**
```
/ban 987654321
```

**Response:**
```
✅ Пользователь 987654321 заблокирован
```

**Notes:**
- Admins cannot ban themselves
- Action is logged with admin ID
- Banned users see an error message when trying to use the bot

### `/unban <user_id>`
Unban a user by their Telegram ID.

**Example:**
```
/unban 987654321
```

**Response:**
```
✅ Пользователь 987654321 разблокирован
```

### `/setrole <user_id> <role>`
Change a user's role.

**Roles:** `admin`, `user`, `guest` (case-insensitive)

**Example:**
```
/setrole 987654321 admin
```

**Response:**
```
✅ Роль пользователя 987654321 изменена на ADMIN
```

**Notes:**
- Use with caution - granting admin role gives full bot control
- Action is logged with admin ID

### `/logs [user_id]`
View audit logs, optionally filtered by user ID (shows last 20 entries).

**Examples:**
```
/logs                  # View all logs
/logs 987654321       # View logs for specific user
```

**Output:**
```
📋 Логи для пользователя 987654321:

2026-01-29 06:00:00
   User: 987654321
   Action: User registered: name='John Doe', role='USER'

2026-01-29 06:05:00
   User: 987654321
   Action: Generated post: 'SMM Москва' (type: text)
```

### `/userinfo <user_id>`
Get detailed information about a specific user.

**Example:**
```
/userinfo 987654321
```

**Output:**
```
👤 Информация о пользователе

ID: 987654321
Имя: John Doe
Username: @johndoe
Роль: USER
Статус: ACTIVE
Premium: ✅ Да
Зарегистрирован: 2026-01-29 06:00:00
Обновлён: 2026-01-29 10:30:00
```

## Initial Setup

### Database Initialization
The database is automatically initialized when the bot starts. Tables are created if they don't exist, and migrations are applied automatically.

### Creating the First Admin

**Method 1: Using init_admin.py script**
```bash
python init_admin.py <telegram_user_id> "Admin Name"
```

Example:
```bash
python init_admin.py 123456789 "Admin Name"
```

**Method 2: Direct SQLite command**
```bash
sqlite3 bot_database.db "UPDATE users SET role='ADMIN' WHERE telegram_id=123456789;"
```

**Method 3: Using Alembic migration**
You can create a data migration to set up initial admin users.

## Database Migrations

The project uses Alembic for database migrations.

### Current Migrations
1. `8af3eec3a7e6` - Initial users and payments tables
2. `add_role_status_logs` - Add role, status fields and logs table

### Running Migrations
```bash
# Apply all pending migrations
alembic upgrade head

# Downgrade to previous version
alembic downgrade -1

# View migration history
alembic history
```

## API Reference

### User Service Functions

All functions are in `services/user_service.py`:

- `register_or_get_user()` - Register new user or update existing user info
- `get_user()` - Get user by Telegram ID
- `update_user_role()` - Change user's role
- `update_user_status()` - Change user's status (ban/unban)
- `is_user_banned()` - Check if user is banned
- `is_user_admin()` - Check if user is an admin
- `get_all_users()` - Get all users (with pagination)
- `add_log()` - Add audit log entry
- `get_logs()` - Get audit logs (with optional user filter)
- `sanitize_for_log()` - Sanitize input for safe logging

## Database Configuration

### Location
Database file: `bot_database.db` (in project root)

The database file is automatically excluded from version control via `.gitignore`.

### Connection
SQLite with async support via aiosqlite:
```
sqlite+aiosqlite:///./bot_database.db
```

### Pooling and Connection Management
- Connection pooling enabled
- Automatic connection verification (pool_pre_ping)
- Connection recycling after 1 hour

## Troubleshooting

### Database locked errors
If you see "database is locked" errors:
1. Ensure only one bot instance is running
2. Check for long-running transactions
3. Consider increasing timeout settings

### Migration issues
If migrations fail:
```bash
# Check current migration version
alembic current

# View pending migrations
alembic upgrade --sql head > migration.sql

# Apply migrations manually if needed
```

### Resetting the database (Development only!)
```bash
rm bot_database.db
python -c "import asyncio; from database.database import init_db; asyncio.run(init_db())"
```

**Warning:** This will delete all user data!

## Best Practices

1. **Regular Backups**: Backup `bot_database.db` regularly
2. **Audit Logs**: Review logs periodically for security monitoring
3. **Admin Access**: Limit admin role to trusted users only
4. **Input Validation**: All user input is sanitized automatically
5. **Database Migrations**: Test migrations in development before production
