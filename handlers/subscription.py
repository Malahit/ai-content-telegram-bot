"""
Subscription handlers for managing premium subscriptions.

This module handles subscription-related commands and payment processing.
"""

from datetime import datetime

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, PreCheckoutQuery
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import config
from logger_config import logger
from services.user_service import get_user, is_premium, add_user
from services.payment_service import create_invoice, handle_pre_checkout, handle_success
from database.models import User


router = Router(name="subscription")


@router.message(Command("subscribe"))
async def subscribe_command(message: Message):
    """
    Handle /subscribe command.
    
    Checks if user is already premium, if not, sends payment invoice.
    
    Args:
        message: Incoming message
    """
    user_id = message.from_user.id
    logger.info(f"User {user_id} requested subscription")
    
    # Check if user is already premium
    user_is_premium = await is_premium(user_id)
    
    if user_is_premium:
        user = await get_user(user_id)
        expiry_str = user.subscription_end.strftime("%Y-%m-%d") if user.subscription_end else "N/A"
        await message.answer(
            f"✅ <b>You already have an active premium subscription!</b>\n\n"
            f"📅 Expires: {expiry_str}\n\n"
            f"Use /status to check your subscription details.",
            parse_mode="HTML"
        )
        return
    
    # Ensure user exists in database
    user = await get_user(user_id)
    if not user:
        user = User(
            telegram_id=user_id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name
        )
        await add_user(user)
        logger.info(f"Created new user {user_id} from subscribe command")
    
    # Create inline keyboard for subscription options
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1 Month - $5.00", callback_data="sub_1")],
        [InlineKeyboardButton(text="3 Months - $12.00 (20% off)", callback_data="sub_3")],
        [InlineKeyboardButton(text="6 Months - $21.00 (30% off)", callback_data="sub_6")],
        [InlineKeyboardButton(text="12 Months - $36.00 (40% off)", callback_data="sub_12")]
    ])
    
    await message.answer(
        "🌟 <b>Premium Subscription</b>\n\n"
        "Get access to exclusive premium features:\n"
        "• 🚀 Priority content generation\n"
        "• 🎨 Unlimited image posts\n"
        "• 📊 Advanced analytics\n"
        "• ⚡ Faster response times\n\n"
        "Choose your subscription plan:",
        reply_markup=keyboard
    )


@router.callback_query(F.data.startswith("sub_"))
async def subscription_callback(callback_query):
    """Handle subscription plan selection."""
    await callback_query.answer()
    
    # Extract months from callback data
    months = int(callback_query.data.split("_")[1])
    user_id = callback_query.from_user.id
    
    # Check if provider token is configured
    if not hasattr(config, 'provider_token') or not config.provider_token:
        await callback_query.message.answer(
            "❌ <b>Payment system not configured</b>\n\n"
            "Please contact the administrator to set up payment processing."
        )
        logger.error("PROVIDER_TOKEN not configured in environment")
        return
    
    try:
        await create_invoice(
            bot=callback_query.bot,
            chat_id=user_id,
            months=months,
            provider_token=config.provider_token
        )
    except Exception as e:
        logger.error(f"Failed to create invoice for user {user_id}: {e}", exc_info=True)
        await callback_query.message.answer(
            "❌ <b>Failed to create payment invoice</b>\n\n"
            "Please try again later or contact support."
        )


@router.pre_checkout_query()
async def pre_checkout_handler(query: PreCheckoutQuery):
    """
    Handle pre-checkout query.
    
    Validates payment before processing.
    
    Args:
        query: PreCheckoutQuery from Telegram
    """
    logger.info(f"Pre-checkout query from user {query.from_user.id}")
    await handle_pre_checkout(query)


@router.message(F.successful_payment)
async def successful_payment_handler(message: Message):
    """
    Handle successful payment.
    
    Activates user's premium subscription.
    
    Args:
        message: Message containing successful payment info
    """
    logger.info(f"Successful payment from user {message.from_user.id}")
    await handle_success(message)


@router.message(Command("status"))
async def status_command(message: Message):
    """
    Handle /status command.
    
    Displays user's subscription status.
    
    Args:
        message: Incoming message
    """
    user_id = message.from_user.id
    user = await get_user(user_id)
    
    if not user:
        await message.answer(
            "ℹ️ <b>Subscription Status</b>\n\n"
            "Status: <b>Free</b>\n\n"
            "Upgrade to premium for exclusive features!\n"
            "Use /subscribe to get started."
        )
        return
    
    user_is_premium = await is_premium(user_id)
    
    if user_is_premium:
        expiry_str = user.subscription_end.strftime("%Y-%m-%d %H:%M UTC") if user.subscription_end else "N/A"
        days_left = (user.subscription_end - datetime.utcnow()).days if user.subscription_end else 0
        
        await message.answer(
            f"✨ <b>Subscription Status</b>\n\n"
            f"Status: <b>Premium</b> 🌟\n"
            f"📅 Expires: {expiry_str}\n"
            f"⏱️ Days remaining: <b>{days_left}</b>\n\n"
            f"Enjoying premium features!"
        )
    else:
        await message.answer(
            "ℹ️ <b>Subscription Status</b>\n\n"
            "Status: <b>Free</b>\n\n"
            "Upgrade to premium for exclusive features!\n"
            "Use /subscribe to get started."
        )
