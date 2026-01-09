"""
User management module for the Telegram bot.
Handles user registration, role management, and status updates with audit logging.
"""
import logging
from typing import Optional
from database import db

logger = logging.getLogger(__name__)


class UserManager:
    """Manages user operations with integrated logging"""
    
    async def register_user(self, user_id: int, name: str, role: str = 'user') -> bool:
        """
        Register a new user and log the action.
        
        Args:
            user_id: Telegram user ID
            name: User's display name
            role: User role (admin, user, guest)
            
        Returns:
            True if successful, False otherwise
        """
        # Add user to database
        user = await db.add_user(user_id, name, role)
        
        if user:
            # Log the registration
            await db.add_log(
                user_id=user_id,
                action=f"User registered: name='{name}', role='{role}'"
            )
            logger.info(f"✅ User {user_id} ({name}) registered with role '{role}'")
            return True
        
        logger.warning(f"⚠️ Failed to register user {user_id}")
        return False
    
    async def change_role(self, user_id: int, new_role: str, admin_id: Optional[int] = None) -> bool:
        """
        Change user's role and log the action.
        
        Args:
            user_id: Telegram user ID
            new_role: New role (admin, user, guest)
            admin_id: ID of admin performing the action (optional)
            
        Returns:
            True if successful, False otherwise
        """
        # Get current user to log old role
        user = await db.get_user(user_id)
        if not user:
            logger.warning(f"User {user_id} not found")
            return False
        
        old_role = user.role
        
        # Update role
        success = await db.update_user_role(user_id, new_role)
        
        if success:
            # Log the role change
            admin_info = f" by admin {admin_id}" if admin_id else ""
            await db.add_log(
                user_id=user_id,
                action=f"Role changed: '{old_role}' → '{new_role}'{admin_info}"
            )
            logger.info(f"✅ User {user_id} role changed: {old_role} → {new_role}{admin_info}")
            return True
        
        logger.warning(f"⚠️ Failed to change role for user {user_id}")
        return False
    
    async def ban_user(self, user_id: int, admin_id: Optional[int] = None) -> bool:
        """
        Ban a user and log the action.
        
        Args:
            user_id: Telegram user ID
            admin_id: ID of admin performing the action (optional)
            
        Returns:
            True if successful, False otherwise
        """
        success = await db.update_user_status(user_id, 'banned')
        
        if success:
            # Log the ban
            admin_info = f" by admin {admin_id}" if admin_id else ""
            await db.add_log(
                user_id=user_id,
                action=f"User banned{admin_info}"
            )
            logger.info(f"✅ User {user_id} banned{admin_info}")
            return True
        
        logger.warning(f"⚠️ Failed to ban user {user_id}")
        return False
    
    async def unban_user(self, user_id: int, admin_id: Optional[int] = None) -> bool:
        """
        Unban a user and log the action.
        
        Args:
            user_id: Telegram user ID
            admin_id: ID of admin performing the action (optional)
            
        Returns:
            True if successful, False otherwise
        """
        success = await db.update_user_status(user_id, 'active')
        
        if success:
            # Log the unban
            admin_info = f" by admin {admin_id}" if admin_id else ""
            await db.add_log(
                user_id=user_id,
                action=f"User unbanned{admin_info}"
            )
            logger.info(f"✅ User {user_id} unbanned{admin_info}")
            return True
        
        logger.warning(f"⚠️ Failed to unban user {user_id}")
        return False
    
    async def is_user_banned(self, user_id: int) -> bool:
        """
        Check if a user is banned.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            True if banned, False otherwise
        """
        user = await db.get_user(user_id)
        return user.status == 'banned' if user else False
    
    async def is_user_admin(self, user_id: int) -> bool:
        """
        Check if a user is an admin.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            True if admin, False otherwise
        """
        user = await db.get_user(user_id)
        return user.role == 'admin' if user else False
    
    async def get_user_info(self, user_id: int) -> Optional[dict]:
        """
        Get user information.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Dictionary with user info or None
        """
        user = await db.get_user(user_id)
        if user:
            return {
                'id': user.id,
                'name': user.name,
                'role': user.role,
                'status': user.status,
                'created_at': user.created_at
            }
        return None


# Global user manager instance
user_manager = UserManager()
