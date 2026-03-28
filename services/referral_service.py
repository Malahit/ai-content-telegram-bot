"""
Referral service module for managing referral system operations.

This module provides functions for generating referral codes,
looking up users by referral code, and crediting referral bonuses.
"""

import secrets
from typing import Optional, List

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from database.models import User
from database.database import AsyncSessionLocal
from logger_config import logger

# Bonus posts per referred friend (permanent daily limit increase)
REFERRAL_BONUS_POSTS = 2


def generate_referral_code() -> str:
    """Generate a unique URL-safe referral code (~8 characters)."""
    return secrets.token_urlsafe(6)


async def ensure_referral_code(telegram_id: int) -> Optional[str]:
    """
    Ensure user has a referral code. Generate one if missing.

    Args:
        telegram_id: The Telegram user ID

    Returns:
        The user's referral code, or None if user not found
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            return None

        if user.referral_code:
            return user.referral_code

        # Generate and save a new code (retry on collision)
        for _ in range(5):
            code = generate_referral_code()
            try:
                user.referral_code = code
                await session.commit()
                await session.refresh(user)
                logger.info(f"Generated referral code for user {telegram_id}: {code}")
                return code
            except IntegrityError:
                await session.rollback()
                # Re-fetch user after rollback
                result = await session.execute(
                    select(User).where(User.telegram_id == telegram_id)
                )
                user = result.scalar_one_or_none()
                if not user:
                    return None
                if user.referral_code:
                    return user.referral_code
                continue

        logger.error(f"Failed to generate unique referral code for user {telegram_id}")
        return None


async def get_user_by_referral_code(referral_code: str) -> Optional[User]:
    """
    Find a user by their referral code.

    Args:
        referral_code: The referral code to look up

    Returns:
        User object if found, None otherwise
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.referral_code == referral_code)
        )
        return result.scalar_one_or_none()


async def credit_referral_bonus(referrer_telegram_id: int, referred_telegram_id: int) -> bool:
    """
    Credit referral bonus to the referrer and mark the referred user.

    Args:
        referrer_telegram_id: Telegram ID of the user who referred
        referred_telegram_id: Telegram ID of the newly referred user

    Returns:
        True if successful, False otherwise
    """
    async with AsyncSessionLocal() as session:
        # Get referrer
        result = await session.execute(
            select(User).where(User.telegram_id == referrer_telegram_id)
        )
        referrer = result.scalar_one_or_none()
        if not referrer:
            return False

        # Get referred user
        result = await session.execute(
            select(User).where(User.telegram_id == referred_telegram_id)
        )
        referred = result.scalar_one_or_none()
        if not referred:
            return False

        # Credit bonus
        referrer.referral_bonus_posts += REFERRAL_BONUS_POSTS
        referrer.referrals_count += 1
        referred.referred_by = referrer_telegram_id

        await session.commit()
        logger.info(
            f"Referral bonus credited: referrer={referrer_telegram_id}, "
            f"referred={referred_telegram_id}, total_bonus={referrer.referral_bonus_posts}"
        )
        return True


async def get_referral_stats(telegram_id: int) -> Optional[dict]:
    """
    Get referral statistics for a user.

    Args:
        telegram_id: The Telegram user ID

    Returns:
        Dict with referral stats, or None if user not found
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            return None

        return {
            "referral_code": user.referral_code,
            "referrals_count": user.referrals_count,
            "bonus_posts": user.referral_bonus_posts,
        }


async def get_top_referrers(limit: int = 10) -> List[dict]:
    """
    Get top referrers by number of referrals.

    Args:
        limit: Maximum number of results

    Returns:
        List of dicts with user info and referral counts
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User)
            .where(User.referrals_count > 0)
            .order_by(User.referrals_count.desc())
            .limit(limit)
        )
        users = result.scalars().all()
        return [
            {
                "username": u.username,
                "telegram_id": u.telegram_id,
                "referrals_count": u.referrals_count,
                "bonus_posts": u.referral_bonus_posts,
            }
            for u in users
        ]
