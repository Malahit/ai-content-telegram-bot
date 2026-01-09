# User Management Features - Documentation

## Overview

The AI Content Telegram Bot now includes comprehensive user management features with role-based access control, user registration, and administrative commands.

## Database Schema

### Users Table

```sql
CREATE TABLE users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'user',
    is_banned INTEGER NOT NULL DEFAULT 0,
    registered_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
```

**Fields:**
- `user_id`: Telegram user ID (primary key)
- `username`: Telegram username (optional)
- `full_name`: User's full name
- `role`: User role (`admin`, `user`, or `guest`)
- `is_banned`: Ban status (0 = not banned, 1 = banned)
- `registered_at`: Registration timestamp (ISO 8601 format)
- `updated_at`: Last update timestamp (ISO 8601 format)

## User Roles

### Available Roles

1. **admin** - Full access to all commands including user management
2. **user** - Standard user access to bot features
3. **guest** - Limited access (guest role)

### Role Permissions

- Only admins can execute: `/set_role`, `/list_users`, `/ban`, `/unban`
- Admin roles cannot be removed or changed (security protection)
- All users can execute: `/register`, `/start`

## Commands

### `/register [Full Name]`

**Description:** Register a new user in the system.

**Usage:**
```
/register John Smith
/register
```

**Behavior:**
- If a name is provided, it will be used
- If no name is provided, the user's Telegram full name will be used
- Name must be 2-100 characters long
- Prevents duplicate registrations
- New users are assigned the `user` role by default

**Examples:**
```
User: /register Alice Johnson
Bot: ✅ Registration Successful!
     👤 Name: Alice Johnson
     🆔 ID: 123456789
     👔 Role: user
```

### `/set_role USER_ID ROLE`

**Description:** Assign a role to a user (admin only).

**Usage:**
```
/set_role 123456789 admin
/set_role 987654321 guest
```

**Parameters:**
- `USER_ID`: Telegram user ID (numeric)
- `ROLE`: One of `admin`, `user`, or `guest`

**Restrictions:**
- Only admins can execute this command
- Cannot change admin roles to prevent accidental admin removal
- Target user must be registered

**Examples:**
```
Admin: /set_role 123456789 admin
Bot: ✅ Role updated: user → admin

Admin: /set_role 111222333 user
Bot: ❌ Cannot change admin role for security reasons
```

### `/list_users [PAGE]`

**Description:** List all registered users with pagination (admin only).

**Usage:**
```
/list_users
/list_users 2
```

**Parameters:**
- `PAGE`: Page number (optional, default is 1)

**Features:**
- Shows 10 users per page
- Displays user status (active/banned)
- Shows role with emoji icons
- Includes registration date

**Example Output:**
```
👥 Users List (Page 1/3)
📊 Total: 25 users

✅ 👑 Admin User
   ID: 111222333 | @adminuser
   Role: admin | Registered: 2026-01-09

✅ 👤 John Smith
   ID: 123456789 | @johnsmith
   Role: user | Registered: 2026-01-09

🚫 👁 Guest User
   ID: 987654321 | —
   Role: guest | Registered: 2026-01-08

💡 Use /list_users 2 for next page
```

### `/ban USER_ID`

**Description:** Ban a user from using the bot (admin only).

**Usage:**
```
/ban 123456789
```

**Restrictions:**
- Only admins can execute this command
- Cannot ban admin users
- User must exist in the database

**Example:**
```
Admin: /ban 123456789
Bot: ✅ User 123456789 has been banned
```

### `/unban USER_ID`

**Description:** Unban a previously banned user (admin only).

**Usage:**
```
/unban 123456789
```

**Restrictions:**
- Only admins can execute this command
- User must be currently banned

**Example:**
```
Admin: /unban 123456789
Bot: ✅ User 123456789 has been unbanned
```

## Database Functions

### Core Functions

#### `init_database()`
Initialize the database and create tables if they don't exist.

#### `register_user(user_id, username, full_name)`
Register a new user. Returns `True` on success, `False` if user already exists.

#### `get_user(user_id)`
Retrieve user information by ID. Returns user dict or `None`.

#### `set_user_role(user_id, new_role, admin_id)`
Update user role. Returns `(success: bool, message: str)`.

#### `ban_user(user_id, admin_id)`
Ban a user. Returns `(success: bool, message: str)`.

#### `unban_user(user_id, admin_id)`
Unban a user. Returns `(success: bool, message: str)`.

#### `list_users(page=1, per_page=10)`
Get paginated user list. Returns `(users: List[Dict], total_users: int, total_pages: int)`.

#### `is_user_admin(user_id)`
Check if user is an admin. Returns `bool`.

#### `is_user_banned(user_id)`
Check if user is banned. Returns `bool`.

## Security Features

1. **Admin Protection**: Admin roles cannot be changed or removed
2. **Admin-Only Commands**: Critical commands require admin privileges
3. **Ban Protection**: Admins cannot be banned
4. **Input Validation**: All user inputs are validated
5. **SQL Injection Protection**: Uses parameterized queries

## Implementation Details

### Database Connection
- Uses SQLite3 with context manager for safe transactions
- Automatic commit on success, rollback on error
- Connection pooling via context manager

### Error Handling
- All database operations wrapped in try-except
- Errors logged via Python logging module
- User-friendly error messages returned

### Decorator Pattern
The `@admin_only` decorator restricts command access:
```python
@dp.message(Command("set_role"))
@admin_only
async def set_role_handler(message: types.Message):
    # Only admins can reach this code
    ...
```

## Setup Instructions

1. The database is automatically initialized when the bot starts
2. Database file: `bot_users.db` (created automatically)
3. Database file is added to `.gitignore` to prevent committing user data

## Migration Notes

For existing deployments:
- Database will be created automatically on first run
- No existing data will be affected
- First admin must be added manually via database or initial setup script

## Example Usage Flow

### Scenario: New User Registration and Admin Setup

```
# Step 1: User registers
User: /register Alice Johnson
Bot: ✅ Registration Successful!

# Step 2: Existing admin promotes user to admin
Admin: /set_role 123456789 admin
Bot: ✅ Role updated: user → admin

# Step 3: New admin can now use admin commands
NewAdmin: /list_users
Bot: [Shows user list]

# Step 4: Admin bans a problematic user
Admin: /ban 999888777
Bot: ✅ User 999888777 has been banned
```

## Troubleshooting

### "User not found" error
- User must register with `/register` before roles can be assigned

### "Access Denied" error
- Only admins can use administrative commands
- Check your role with an existing admin using `/list_users`

### Database errors
- Check file permissions on `bot_users.db`
- Ensure disk space is available
- Check logs for detailed error messages

## Future Enhancements

Potential improvements:
- User profile management
- Activity logging
- User statistics
- Role permissions customization
- Automated admin assignment
- User search functionality
