# User Management System

This document describes the user management features of the AI Content Telegram Bot.

## Features

### 1. User Registration
- Users can register via the `/register` command
- Auto-registration on first interaction with the bot
- User data stored includes:
  - **ID**: Unique Telegram user ID
  - **Name**: Retrieved from Telegram profile
  - **Role**: `admin`, `user`, or `guest`
  - **Status**: `active` or `banned`
  - **Timestamps**: Created and updated dates

### 2. User Roles and Permissions

#### Role Hierarchy
1. **Admin** - Full access to all bot features and management commands
2. **User** - Can generate content and use bot features
3. **Guest** - Limited access (help and status commands only)

#### Role Permissions
- **Admin**:
  - All user permissions
  - List all users (`/list_users`)
  - Ban/unban users (`/ban`, `/unban`)
  - Assign roles (`/set_role`)
  
- **User**:
  - Generate AI content posts
  - Use all bot features
  
- **Guest**:
  - View help and status
  - Cannot generate content
  - Must request role upgrade from admin

### 3. Admin Commands

#### `/list_users`
Lists all registered users with their details.

**Usage:**
```
/list_users
```

**Output:**
```
👥 Список пользователей:

✅ 👑 John Admin
   ID: 123456789 | admin | active

✅ 👤 Jane User
   ID: 987654321 | user | active
```

#### `/ban <user_id>`
Ban a user from using the bot.

**Usage:**
```
/ban 987654321
```

**Example:**
```
/ban 987654321

🚫 Пользователь заблокирован
ID: 987654321
Имя: Jane User
```

#### `/unban <user_id>`
Unban a previously banned user.

**Usage:**
```
/unban 987654321
```

#### `/set_role <user_id> <role>`
Change a user's role.

**Usage:**
```
/set_role <user_id> <role>
```

**Available roles:** `admin`, `user`, `guest`

**Example:**
```
/set_role 987654321 user

✅ Роль изменена
ID: 987654321
Имя: Jane User
Новая роль: user
```

### 4. User Commands

#### `/register`
Register or view your registration information.

**Usage:**
```
/register
```

**Example (new user):**
```
🎉 Регистрация успешна!
👤 ID: 987654321
📝 Имя: Jane User
🎭 Роль: guest
📊 Статус: active
```

**Example (existing user):**
```
✅ Вы уже зарегистрированы!
👤 ID: 987654321
📝 Имя: Jane User
🎭 Роль: user
📊 Статус: active
📅 Дата регистрации: 2026-01-08 23:00:00
```

#### `/help`
Display available commands based on your role.

**Usage:**
```
/help
```

## Database Setup

### Initial Setup

1. **Environment Variables**

Create or update your `.env` file:

```bash
BOT_TOKEN=your_telegram_bot_token
PPLX_API_KEY=your_perplexity_api_key
CHANNEL_ID=@your_channel
ADMIN_IDS=123456789,987654321  # Comma-separated admin Telegram IDs
DB_PATH=bot_users.db  # Optional, defaults to bot_users.db
```

2. **Install Dependencies**

```bash
pip install -r requirements.txt
```

3. **Initialize Database**

The database will be automatically initialized when the bot starts. Alternatively, you can use the setup script:

```bash
python setup_db.py init
```

### Setup Script Usage

The `setup_db.py` script provides utilities for database management:

#### Initialize Database
```bash
python setup_db.py init
```

#### Create Admin User
```bash
python setup_db.py create_admin <user_id> <name>
```

Example:
```bash
python setup_db.py create_admin 123456789 "John Admin"
```

#### List All Users
```bash
python setup_db.py list
```

### Database Schema

**Table: users**

| Column     | Type      | Description                          |
|------------|-----------|--------------------------------------|
| id         | INTEGER   | Primary key (Telegram user ID)      |
| name       | TEXT      | User's display name                  |
| role       | TEXT      | User role (admin/user/guest)         |
| status     | TEXT      | Account status (active/banned)       |
| created_at | TIMESTAMP | Registration timestamp               |
| updated_at | TIMESTAMP | Last update timestamp                |

**Constraints:**
- Role must be one of: `admin`, `user`, `guest`
- Status must be one of: `active`, `banned`

## Logging

All user actions and admin operations are logged for auditing:

- User registrations
- Role changes
- Ban/unban operations
- Content generation requests
- Unauthorized access attempts

Logs are written to the standard logging output and can be viewed in the bot console or server logs.

## Security Considerations

1. **Admin Assignment**: Admins must be defined in the `.env` file via `ADMIN_IDS`
2. **Self-Ban Protection**: Users cannot ban themselves
3. **Access Control**: All commands check user permissions before execution
4. **Banned Users**: Banned users are immediately blocked from all bot features
5. **Audit Trail**: All admin actions are logged for accountability

## Usage Examples

### Example Workflow: New User

1. User starts bot: `/start`
2. Bot auto-registers user as `guest`
3. User tries to generate content: **Access denied**
4. User requests help: `/help`
5. Admin upgrades user: `/set_role <user_id> user`
6. User can now generate content

### Example Workflow: Admin Management

1. Admin lists users: `/list_users`
2. Admin identifies problematic user
3. Admin bans user: `/ban <user_id>`
4. Later, admin unbans: `/unban <user_id>`
5. Admin assigns new role: `/set_role <user_id> user`

## Troubleshooting

### Database Not Found
- Ensure the bot has write permissions in the directory
- Check `DB_PATH` in `.env` if specified
- Run `python setup_db.py init` to manually create database

### Admin Commands Not Working
- Verify your Telegram ID is in `ADMIN_IDS` in `.env`
- Restart the bot after updating `.env`
- Check logs for permission errors

### User Not Registered
- Use `/register` command explicitly
- Check database with `python setup_db.py list`
- Verify database file exists and is accessible

## Migration from Previous Version

If upgrading from a version without user management:

1. Install new dependencies: `pip install -r requirements.txt`
2. Add `ADMIN_IDS` to your `.env` file
3. Start the bot (database will be created automatically)
4. Existing users will be auto-registered on next interaction
5. Use `/set_role` to assign appropriate roles

## Backup and Recovery

### Backup Database
```bash
cp bot_users.db bot_users.db.backup
```

### Restore Database
```bash
cp bot_users.db.backup bot_users.db
```

### Export Users (Manual)
```bash
python setup_db.py list > users_backup.txt
```
