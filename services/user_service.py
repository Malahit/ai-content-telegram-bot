"""
User service module for managing user-related operations.

This module provides functions for user management and subscription handling.
"""

from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User, Log, UserRole, UserStatus
from database.database import AsyncSessionLocal
from logger_config import logger


# Constants
DAYS_PER_MONTH = 30  # Simplified calculation for subscription periods


def sanitize_for_log(text: str) -> str:
    """
    Sanitize user input for logging to prevent log injection.
    
    Args:
        text: Input text to sanitize
        
    Returns:
        Sanitized text safe for logging
    """
    if not text:
        return ""
    # Replace newlines and carriage returns with spaces
    sanitized = text.replace('\n', ' ').replace('\r', ' ')
    # Limit length to prevent log flooding
    if len(sanitized) > 200:
        sanitized = sanitized[:200] + "..."
    return sanitized


async def add_user(user: User) -> User:
    """
    Add a new user to the database.
    
    Args:
        user: User object to add
        
    Returns:
        User: The added user with ID assigned
    """
    async with AsyncSessionLocal() as session:
        session.add(user)
        await session.commit()
        await session.refresh(user)
        logger.info(f"Added new user: telegram_id={user.telegram_id}")
        return user


async def get_user(telegram_id: int) -> Optional[User]:
    """
    Retrieve a user by their Telegram ID.
    
    Args:
        telegram_id: The Telegram user ID
        
    Returns:
        User object if found, None otherwise
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        return user


async def activate_subscription(telegram_id: int, months: int = 1) -> Optional[User]:
    """
    Update user's subscription settings.
    
    Args:
        telegram_id: The Telegram user ID
        months: Number of months to add to subscription (default: 1)
        
    Returns:
        Updated User object if found, None otherwise
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        
        if user:
            # Calculate new subscription end date
            now = datetime.utcnow()
            
            # If user already has an active subscription, extend from current end date
            if user.subscription_end and user.subscription_end > now:
                user.subscription_end = user.subscription_end + timedelta(days=months * DAYS_PER_MONTH)
            else:
                # Otherwise, start from now
                user.subscription_end = now + timedelta(days=months * DAYS_PER_MONTH)
            
            user.is_premium = True
            user.updated_at = now
            
            await session.commit()
            await session.refresh(user)
            logger.info(f"Activated subscription for user {telegram_id}: {months} month(s), expires {user.subscription_end}")
            return user
        
        logger.warning(f"User {telegram_id} not found for subscription activation")
        return None


async def is_premium(telegram_id: int) -> bool:
    """
    Check if user has premium access.
    
    Args:
        telegram_id: The Telegram user ID
        
    Returns:
        bool: True if user has active premium subscription, False otherwise
    """
    user = await get_user(telegram_id)
    
    if not user or not user.is_premium:
        return False
    
    # Check if subscription is still valid
    if user.subscription_end:
        now = datetime.utcnow()
        if user.subscription_end < now:
            # Subscription expired, deactivate premium status
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(User).where(User.telegram_id == telegram_id)
                )
                expired_user = result.scalar_one_or_none()
                if expired_user:
                    expired_user.is_premium = False
                    expired_user.updated_at = now
                    await session.commit()
                    logger.info(f"Deactivated expired subscription for user {telegram_id}")
            return False
    
    return True


async def count_premium() -> int:
    """
    Count the number of premium users.
    
    Returns:
        int: Number of users with active premium subscriptions
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(func.count(User.id)).where(User.is_premium.is_(True))
        )
        count = result.scalar()
        return count or 0


async def register_or_get_user(
    telegram_id: int,
    username: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    role: UserRole = UserRole.USER
) -> User:
    """
    Register a new user or get existing user and log the action.
    
    Args:
        telegram_id: Telegram user ID
        username: User's username
        first_name: User's first name
        last_name: User's last name
        role: User role (default: UserRole.USER)
        
    Returns:
        User object
    """
    async with AsyncSessionLocal() as session:
        # Check if user exists
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        
        if user:
            # Update user info if changed
            updated = False
            if username and user.username != username:
                user.username = username
                updated = True
            if first_name and user.first_name != first_name:
                user.first_name = first_name
                updated = True
            if last_name and user.last_name != last_name:
                user.last_name = last_name
                updated = True
                
            if updated:
                user.updated_at = datetime.utcnow()
                await session.commit()
                await session.refresh(user)
                logger.info(f"Updated user info for {telegram_id}")
        else:
            # Create new user
            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                role=role,
                status=UserStatus.ACTIVE
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            
            # Log registration
            safe_name = sanitize_for_log(first_name or username or str(telegram_id))
            await add_log(
                telegram_id=telegram_id,
                action=f"User registered: name='{safe_name}', role='{role.value}'"
            )
            logger.info(f"✅ User {telegram_id} ({safe_name}) registered with role '{role.value}'")
        
        return user


async def update_user_role(telegram_id: int, new_role: UserRole, admin_id: Optional[int] = None) -> bool:
    """
    Change user's role and log the action.
    
    Args:
        telegram_id: Telegram user ID
        new_role: New role
        admin_id: ID of admin performing the action (optional)
        
    Returns:
        True if successful, False otherwise
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            logger.warning(f"User {telegram_id} not found")
            return False
        
        old_role = user.role
        user.role = new_role
        user.updated_at = datetime.utcnow()
        
        await session.commit()
        
        # Log the role change
        admin_info = f" by admin {admin_id}" if admin_id else ""
        await add_log(
            telegram_id=telegram_id,
            action=f"Role changed: '{old_role.value}' → '{new_role.value}'{admin_info}"
        )
        logger.info(f"✅ User {telegram_id} role changed to '{new_role.value}'{admin_info}")
        return True


async def update_user_status(telegram_id: int, new_status: UserStatus, admin_id: Optional[int] = None) -> bool:
    """
    Change user's status and log the action.
    
    Args:
        telegram_id: Telegram user ID
        new_status: New status
        admin_id: ID of admin performing the action (optional)
        
    Returns:
        True if successful, False otherwise
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            logger.warning(f"User {telegram_id} not found")
            return False
        
        old_status = user.status
        user.status = new_status
        user.updated_at = datetime.utcnow()
        
        await session.commit()
        
        # Log the status change
        admin_info = f" by admin {admin_id}" if admin_id else ""
        await add_log(
            telegram_id=telegram_id,
            action=f"Status changed: '{old_status.value}' → '{new_status.value}'{admin_info}"
        )
        logger.info(f"✅ User {telegram_id} status changed to '{new_status.value}'{admin_info}")
        return True


async def is_user_banned(telegram_id: int) -> bool:
    """
    Check if user is banned.
    
    Args:
        telegram_id: Telegram user ID
        
    Returns:
        True if user is banned, False otherwise
    """
    user = await get_user(telegram_id)
    return user.status == UserStatus.BANNED if user else False


async def is_user_admin(telegram_id: int) -> bool:
    """
    Check if user is an admin.
    
    Args:
        telegram_id: Telegram user ID
        
    Returns:
        True if user is an admin, False otherwise
    """
    user = await get_user(telegram_id)
    return user.role == UserRole.ADMIN if user else False


async def get_all_users(limit: int = 100, offset: int = 0):
    """
    Get all users with pagination.
    
    Args:
        limit: Maximum number of users to return
        offset: Number of users to skip
        
    Returns:
        List of User objects
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).limit(limit).offset(offset)
        )
        users = result.scalars().all()
        return users


async def add_log(telegram_id: int, action: str) -> None:
    """
    Add a log entry for user action.
    
    Args:
        telegram_id: Telegram user ID
        action: Description of the action
    """
    async with AsyncSessionLocal() as session:
        log_entry = Log(
            user_id=telegram_id,
            action=sanitize_for_log(action)
        )
        session.add(log_entry)
        await session.commit()


async def get_logs(telegram_id: Optional[int] = None, limit: int = 100):
    """
    Get log entries, optionally filtered by user.
    
    Args:
        telegram_id: Optional Telegram user ID to filter logs
        limit: Maximum number of logs to return
        
    Returns:
        List of Log objects
    """
    async with AsyncSessionLocal() as session:
        query = select(Log).order_by(Log.timestamp.desc()).limit(limit)
        
        if telegram_id:
            query = query.where(Log.user_id == telegram_id)
        
        result = await session.execute(query)
        logs = result.scalars().all()
        return logs
