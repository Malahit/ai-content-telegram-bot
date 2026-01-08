"""
Database module for user management in AI Content Telegram Bot.
Uses SQLite with aiosqlite for async operations.
"""
import aiosqlite
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict
import os

logger = logging.getLogger(__name__)

DB_PATH = os.getenv("DB_PATH", "bot_users.db")


class Database:
    """Database handler for user management."""
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        
    async def init_db(self):
        """Initialize database with users table."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'guest',
                    status TEXT NOT NULL DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT role_check CHECK (role IN ('admin', 'user', 'guest')),
                    CONSTRAINT status_check CHECK (status IN ('active', 'banned'))
                )
            """)
            await db.commit()
            logger.info(f"✅ Database initialized at {self.db_path}")
    
    async def register_user(self, user_id: int, name: str, role: str = 'guest') -> bool:
        """Register a new user or update existing user."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Check if user exists
                cursor = await db.execute("SELECT id FROM users WHERE id = ?", (user_id,))
                existing = await cursor.fetchone()
                
                if existing:
                    # Update existing user
                    await db.execute(
                        "UPDATE users SET name = ?, updated_at = ? WHERE id = ?",
                        (name, datetime.now(timezone.utc), user_id)
                    )
                    logger.info(f"Updated user: {user_id} ({name})")
                else:
                    # Insert new user
                    await db.execute(
                        "INSERT INTO users (id, name, role, status) VALUES (?, ?, ?, ?)",
                        (user_id, name, role, 'active')
                    )
                    logger.info(f"Registered new user: {user_id} ({name}) as {role}")
                
                await db.commit()
                return True
        except Exception as e:
            logger.error(f"Error registering user {user_id}: {e}")
            return False
    
    async def get_user(self, user_id: int) -> Optional[Dict]:
        """Get user information by ID."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(
                    "SELECT id, name, role, status, created_at FROM users WHERE id = ?",
                    (user_id,)
                )
                row = await cursor.fetchone()
                if row:
                    return dict(row)
                return None
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {e}")
            return None
    
    async def list_users(self, status: Optional[str] = None) -> List[Dict]:
        """List all users, optionally filtered by status."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                if status:
                    cursor = await db.execute(
                        "SELECT id, name, role, status, created_at FROM users WHERE status = ? ORDER BY created_at DESC",
                        (status,)
                    )
                else:
                    cursor = await db.execute(
                        "SELECT id, name, role, status, created_at FROM users ORDER BY created_at DESC"
                    )
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error listing users: {e}")
            return []
    
    async def update_user_role(self, user_id: int, role: str) -> bool:
        """Update user role."""
        if role not in ['admin', 'user', 'guest']:
            logger.error(f"Invalid role: {role}")
            return False
        
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "UPDATE users SET role = ?, updated_at = ? WHERE id = ?",
                    (role, datetime.now(timezone.utc), user_id)
                )
                await db.commit()
                logger.info(f"Updated user {user_id} role to {role}")
                return True
        except Exception as e:
            logger.error(f"Error updating user {user_id} role: {e}")
            return False
    
    async def update_user_status(self, user_id: int, status: str) -> bool:
        """Update user status (active/banned)."""
        if status not in ['active', 'banned']:
            logger.error(f"Invalid status: {status}")
            return False
        
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "UPDATE users SET status = ?, updated_at = ? WHERE id = ?",
                    (status, datetime.now(timezone.utc), user_id)
                )
                await db.commit()
                logger.info(f"Updated user {user_id} status to {status}")
                return True
        except Exception as e:
            logger.error(f"Error updating user {user_id} status: {e}")
            return False
    
    async def ban_user(self, user_id: int) -> bool:
        """Ban a user."""
        return await self.update_user_status(user_id, 'banned')
    
    async def unban_user(self, user_id: int) -> bool:
        """Unban a user."""
        return await self.update_user_status(user_id, 'active')


# Global database instance
db = Database()
