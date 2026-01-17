"""
CRON job utilities for subscription management.

This module handles scheduled tasks for subscription expiration and user management.
"""

from datetime import datetime
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
from sqlalchemy import select

from database.models import User
from database.database import AsyncSessionLocal
from logger_config import logger
from config import config


async def check_expired_subscriptions(bot: Optional[Bot] = None) -> None:
    """
    Check for expired subscriptions and deactivate them.
    
    This function runs periodically to ensure users with expired subscriptions
    lose their premium status.
    
    Args:
        bot: Optional Bot instance for sending notifications to users
    """
    now = datetime.utcnow()
    logger.info("Running subscription expiration check...")
    
    async with AsyncSessionLocal() as session:
        # Find users with expired subscriptions that are still marked as premium
        result = await session.execute(
            select(User).where(
                User.is_premium.is_(True),
                User.subscription_end < now
            )
        )
        expired_users = result.scalars().all()
        
        if not expired_users:
            logger.info("No expired subscriptions found")
            return
        
        logger.info(f"Found {len(expired_users)} expired subscriptions")
        
        for user in expired_users:
            try:
                # Deactivate premium status
                user.is_premium = False
                user.updated_at = now
                
                logger.info(
                    f"Deactivated expired subscription for user {user.telegram_id}, "
                    f"expired at {user.subscription_end}"
                )
                
                # Optionally send notification to user
                if bot:
                    try:
                        await bot.send_message(
                            chat_id=user.telegram_id,
                            text=(
                                "⏰ <b>Subscription Expired</b>\n\n"
                                "Your premium subscription has expired.\n\n"
                                "Renew now to continue enjoying premium features!\n"
                                "Use /subscribe to renew."
                            ),
                            parse_mode="HTML"
                        )
                        logger.info(f"Sent expiration notification to user {user.telegram_id}")
                    except Exception as e:
                        logger.error(
                            f"Failed to send expiration notification to user {user.telegram_id}: {e}"
                        )
                
            except Exception as e:
                logger.error(f"Error deactivating subscription for user {user.telegram_id}: {e}")
        
        # Commit all changes
        await session.commit()
        logger.info(f"Subscription expiration check completed: {len(expired_users)} users deactivated")


def setup_expiration_job(scheduler: AsyncIOScheduler, bot: Optional[Bot] = None) -> None:
    """
    Setup the scheduled job for checking subscription expirations.
    
    Args:
        scheduler: APScheduler instance
        bot: Optional Bot instance for sending notifications
    """
    # Run every day at midnight UTC
    scheduler.add_job(
        check_expired_subscriptions,
        'cron',
        hour=0,
        minute=0,
        args=[bot],
        id='check_expired_subscriptions',
        replace_existing=True
    )
    
    logger.info("Subscription expiration job scheduled: runs daily at 00:00 UTC")
