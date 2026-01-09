"""
Database module for user management in the Telegram bot.
Handles user registration, roles, and banning functionality.
"""

import sqlite3
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

logger = logging.getLogger(__name__)

DATABASE_PATH = "bot_users.db"

# Role constants
ROLE_ADMIN = "admin"
ROLE_USER = "user"
ROLE_GUEST = "guest"
VALID_ROLES = {ROLE_ADMIN, ROLE_USER, ROLE_GUEST}


@contextmanager
def get_db_connection():
    """Context manager for database connections."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        conn.close()


def init_database():
    """Initialize the database with required tables."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                is_banned INTEGER NOT NULL DEFAULT 0,
                registered_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        logger.info("✅ Database initialized successfully")


def register_user(user_id: int, username: Optional[str], full_name: str) -> bool:
    """
    Register a new user in the database.
    
    Args:
        user_id: Telegram user ID
        username: Telegram username (optional)
        full_name: User's full name
    
    Returns:
        True if registration successful, False if user already exists
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now(timezone.utc).isoformat()
            
            # Check if user already exists
            cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
            if cursor.fetchone():
                return False
            
            cursor.execute("""
                INSERT INTO users (user_id, username, full_name, role, registered_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, username, full_name, ROLE_USER, now, now))
            
            logger.info(f"✅ User registered: {user_id} ({full_name})")
            return True
    except Exception as e:
        logger.error(f"Failed to register user {user_id}: {e}")
        return False


def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    """
    Get user information by user_id.
    
    Args:
        user_id: Telegram user ID
    
    Returns:
        User data as dictionary or None if not found
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    except Exception as e:
        logger.error(f"Failed to get user {user_id}: {e}")
        return None


def set_user_role(user_id: int, new_role: str, admin_id: int) -> tuple[bool, str]:
    """
    Set user role. Admins cannot have their role changed by other admins.
    
    Args:
        user_id: Telegram user ID to modify
        new_role: New role to assign (admin, user, guest)
        admin_id: ID of admin making the change
    
    Returns:
        Tuple of (success: bool, message: str)
    """
    if new_role not in VALID_ROLES:
        return False, f"❌ Invalid role. Must be one of: {', '.join(VALID_ROLES)}"
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get current user info
            cursor.execute("SELECT role FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            
            if not row:
                return False, "❌ User not found. They must register first with /register"
            
            current_role = row['role']
            
            # Prevent changing admin role (protection against admin removal)
            if current_role == ROLE_ADMIN and new_role != ROLE_ADMIN:
                return False, "❌ Cannot change admin role for security reasons"
            
            # Update role
            now = datetime.now(timezone.utc).isoformat()
            cursor.execute("""
                UPDATE users 
                SET role = ?, updated_at = ?
                WHERE user_id = ?
            """, (new_role, now, user_id))
            
            logger.info(f"✅ Role changed for user {user_id}: {current_role} → {new_role} by admin {admin_id}")
            return True, f"✅ Role updated: {current_role} → {new_role}"
    except Exception as e:
        logger.error(f"Failed to set role for user {user_id}: {e}")
        return False, f"❌ Database error: {str(e)}"


def ban_user(user_id: int, admin_id: int) -> tuple[bool, str]:
    """
    Ban a user. Admins cannot be banned.
    
    Args:
        user_id: Telegram user ID to ban
        admin_id: ID of admin performing the ban
    
    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get user info
            cursor.execute("SELECT role, is_banned FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            
            if not row:
                return False, "❌ User not found"
            
            if row['role'] == ROLE_ADMIN:
                return False, "❌ Cannot ban admin users"
            
            if row['is_banned']:
                return False, "⚠️ User is already banned"
            
            # Ban user
            now = datetime.now(timezone.utc).isoformat()
            cursor.execute("""
                UPDATE users 
                SET is_banned = 1, updated_at = ?
                WHERE user_id = ?
            """, (now, user_id))
            
            logger.info(f"✅ User {user_id} banned by admin {admin_id}")
            return True, f"✅ User {user_id} has been banned"
    except Exception as e:
        logger.error(f"Failed to ban user {user_id}: {e}")
        return False, f"❌ Database error: {str(e)}"


def unban_user(user_id: int, admin_id: int) -> tuple[bool, str]:
    """
    Unban a user.
    
    Args:
        user_id: Telegram user ID to unban
        admin_id: ID of admin performing the unban
    
    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get user info
            cursor.execute("SELECT is_banned FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            
            if not row:
                return False, "❌ User not found"
            
            if not row['is_banned']:
                return False, "⚠️ User is not banned"
            
            # Unban user
            now = datetime.now(timezone.utc).isoformat()
            cursor.execute("""
                UPDATE users 
                SET is_banned = 0, updated_at = ?
                WHERE user_id = ?
            """, (now, user_id))
            
            logger.info(f"✅ User {user_id} unbanned by admin {admin_id}")
            return True, f"✅ User {user_id} has been unbanned"
    except Exception as e:
        logger.error(f"Failed to unban user {user_id}: {e}")
        return False, f"❌ Database error: {str(e)}"


def list_users(page: int = 1, per_page: int = 10) -> tuple[List[Dict[str, Any]], int, int]:
    """
    Get paginated list of all users.
    
    Args:
        page: Page number (1-indexed)
        per_page: Number of users per page
    
    Returns:
        Tuple of (users: List[Dict], total_users: int, total_pages: int)
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get total count
            cursor.execute("SELECT COUNT(*) as count FROM users")
            total_users = cursor.fetchone()['count']
            total_pages = (total_users + per_page - 1) // per_page  # Ceiling division
            
            # Get paginated users
            offset = (page - 1) * per_page
            cursor.execute("""
                SELECT user_id, username, full_name, role, is_banned, registered_at
                FROM users
                ORDER BY registered_at DESC
                LIMIT ? OFFSET ?
            """, (per_page, offset))
            
            users = [dict(row) for row in cursor.fetchall()]
            return users, total_users, total_pages
    except Exception as e:
        logger.error(f"Failed to list users: {e}")
        return [], 0, 0


def is_user_admin(user_id: int) -> bool:
    """
    Check if user has admin role.
    
    Args:
        user_id: Telegram user ID
    
    Returns:
        True if user is admin, False otherwise
    """
    user = get_user(user_id)
    return user is not None and user['role'] == ROLE_ADMIN


def is_user_banned(user_id: int) -> bool:
    """
    Check if user is banned.
    
    Args:
        user_id: Telegram user ID
    
    Returns:
        True if user is banned, False otherwise
    """
    user = get_user(user_id)
    return user is not None and user['is_banned'] == 1
