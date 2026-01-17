"""
User service module for managing user-related operations.

This module provides functions for user management and subscription handling.
"""

from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User
from database.database import AsyncSessionLocal
from logger_config import logger


# Constants
DAYS_PER_MONTH = 30  # Simplified calculation for subscription periods


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
