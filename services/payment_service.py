"""
Payment service module for managing payment-related operations.

This module provides functions for creating invoices and handling payments.
"""

from datetime import datetime
from typing import Optional
import json

from aiogram import Bot
from aiogram.types import LabeledPrice, PreCheckoutQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Payment, PaymentStatus, User
from database.database import AsyncSessionLocal
from services.user_service import activate_subscription, get_user, add_user
from logger_config import logger


async def create_invoice(
    bot: Bot,
    chat_id: int,
    months: int = 1,
    provider_token: str = None
) -> None:
    """
    Create and send a subscription invoice to the user.
    
    Args:
        bot: Telegram bot instance
        chat_id: Chat ID to send invoice to
        months: Number of subscription months (default: 1)
        provider_token: Payment provider token
    """
    # Define pricing based on months
    prices_map = {
        1: 50000,  # $5.00 for 1 month
        3: 120000,  # $12.00 for 3 months (20% discount)
        6: 210000,  # $21.00 for 6 months (30% discount)
        12: 360000  # $36.00 for 12 months (40% discount)
    }
    
    price = prices_map.get(months, 50000 * months)
    
    # Create payment payload with metadata
    payload = json.dumps({
        "user_id": chat_id,
        "months": months,
        "timestamp": datetime.utcnow().isoformat()
    })
    
    title = f"Premium Subscription - {months} month{'s' if months > 1 else ''}"
    description = f"Unlock premium features for {months} month{'s' if months > 1 else ''}"
    
    try:
        await bot.send_invoice(
            chat_id=chat_id,
            title=title,
            description=description,
            payload=payload,
            provider_token=provider_token,
            currency='USD',
            prices=[LabeledPrice(label=title, amount=price)],
            start_parameter='subscription',
            need_name=False,
            need_phone_number=False,
            need_email=False,
            need_shipping_address=False,
            is_flexible=False
        )
        logger.info(f"Invoice sent to chat_id={chat_id} for {months} month(s), amount={price}")
    except Exception as e:
        logger.error(f"Failed to send invoice to chat_id={chat_id}: {e}", exc_info=True)
        raise


async def handle_pre_checkout(query: PreCheckoutQuery) -> None:
    """
    Handle pre-checkout query from Telegram.
    
    This function validates the payment before it's processed.
    
    Args:
        query: PreCheckoutQuery object from Telegram
    """
    try:
        # Parse payload
        payload_data = json.loads(query.invoice_payload)
        user_id = payload_data.get('user_id')
        months = payload_data.get('months', 1)
        
        # Create pending payment record
        async with AsyncSessionLocal() as session:
            payment = Payment(
                user_id=user_id,
                amount=query.total_amount,
                currency=query.currency,
                status=PaymentStatus.PENDING,
                provider=query.provider_payment_charge_id or "telegram",
                payload=payload_data
            )
            session.add(payment)
            await session.commit()
            logger.info(f"Created pending payment record for user {user_id}, amount={query.total_amount}")
        
        # Approve the checkout
        await query.answer(ok=True)
        logger.info(f"Pre-checkout approved for user {user_id}")
        
    except Exception as e:
        logger.error(f"Pre-checkout error: {e}", exc_info=True)
        await query.answer(ok=False, error_message="Payment validation failed. Please try again.")


async def handle_success(message: Message) -> None:
    """
    Handle successful payment.
    
    This function is called when a payment is successfully completed.
    It activates the user's subscription.
    
    Args:
        message: Message object containing successful payment info
    """
    try:
        payment_info = message.successful_payment
        
        # Parse payload to get subscription details
        payload_data = json.loads(payment_info.invoice_payload)
        user_id = payload_data.get('user_id')
        months = payload_data.get('months', 1)
        
        # Ensure user exists in database
        user = await get_user(user_id)
        if not user:
            # Create user if doesn't exist
            user = User(
                telegram_id=user_id,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name
            )
            user = await add_user(user)
            logger.info(f"Created new user {user_id} from successful payment")
        
        # Activate subscription
        await activate_subscription(user_id, months=months)
        
        # Update payment record to success
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Payment).where(
                    Payment.user_id == user_id,
                    Payment.status == PaymentStatus.PENDING
                ).order_by(Payment.created_at.desc())
            )
            payment = result.scalar_one_or_none()
            
            if payment:
                payment.status = PaymentStatus.SUCCESS
                payment.paid_at = datetime.utcnow()
                payment.provider = payment_info.provider_payment_charge_id or payment.provider
                await session.commit()
                logger.info(f"Payment successful for user {user_id}, payment_id={payment.id}")
        
        # Send confirmation message
        await message.answer(
            f"✅ <b>Payment Successful!</b>\n\n"
            f"🎉 Your premium subscription has been activated for <b>{months} month{'s' if months > 1 else ''}</b>.\n"
            f"💰 Amount: ${payment_info.total_amount / 100:.2f}\n\n"
            f"Enjoy your premium features!",
            parse_mode="HTML"
        )
        logger.info(f"Subscription activated for user {user_id}: {months} month(s)")
        
    except Exception as e:
        logger.error(f"Error handling successful payment: {e}", exc_info=True)
        await message.answer(
            "⚠️ Payment received but there was an error activating your subscription. "
            "Please contact support with your payment details."
        )
