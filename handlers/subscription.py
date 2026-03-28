"""
Subscription handlers — Telegram Stars payment for Pro subscription.

Plans:
  week   — 25⭐ (7 days, one-time)
  month  — 75⭐ (30 days, recurring via subscription_period)
  quarter— 200⭐ (90 days, one-time)
  year   — 600⭐ (365 days, one-time)
"""

import os
from datetime import datetime, timedelta

from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import (
    Message,
    PreCheckoutQuery,
    LabeledPrice,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from config import config
from logger_config import logger
from services.user_service import get_user, is_premium as check_is_premium, register_or_get_user
from services.usage_service import get_today_post_count, get_total_post_count
from database.database import AsyncSessionLocal
from database.models import Payment, PaymentStatus, User

router = Router(name="subscription")

SUBSCRIPTION_PLANS = {
    "week": {"stars": 25, "days": 7, "label": "Пробная неделя"},
    "month": {"stars": 75, "days": 30, "label": "Месяц"},
    "quarter": {"stars": 200, "days": 90, "label": "3 месяца"},
    "year": {"stars": 600, "days": 365, "label": "Год"},
}

FREE_DAILY_LIMIT = int(os.getenv("FREE_DAILY_LIMIT", "3"))
PRO_DAILY_LIMIT = int(os.getenv("PRO_DAILY_LIMIT", "30"))


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    value = value.strip().lower()
    if value in {"1", "true", "yes", "y", "on"}:
        return True
    if value in {"0", "false", "no", "n", "off"}:
        return False
    return default


def payments_enabled() -> bool:
    return _env_bool("PAYMENTS_ENABLED", True)


@router.message(Command("subscribe"))
async def subscribe_command(message: Message):
    """Show subscription plans with inline keyboard."""
    user_id = message.from_user.id
    logger.info(f"User {user_id} requested /subscribe")

    if not payments_enabled():
        is_admin = user_id in getattr(config, "admin_user_ids", [])
        if is_admin:
            await message.answer(
                "💳 <b>Платежи отключены администратором</b>\n\n"
                "Чтобы включить: <code>PAYMENTS_ENABLED=true</code>",
                parse_mode="HTML",
            )
        else:
            await message.answer(
                "💳 <b>Платежи временно отключены</b>\n\n"
                "Попробуй позже или свяжись с администратором.",
                parse_mode="HTML",
            )
        return

    user_is_premium = await check_is_premium(user_id)
    if user_is_premium:
        user = await get_user(user_id)
        expiry_str = (
            user.subscription_end.strftime("%d.%m.%Y")
            if user and user.subscription_end
            else "N/A"
        )
        await message.answer(
            f"✅ <b>У вас уже есть активная подписка Pro!</b>\n\n"
            f"📅 Действует до: {expiry_str}\n\n"
            f"Используйте /status для деталей.",
            parse_mode="HTML",
        )
        return

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text=f"⭐ {p['label']} — {p['stars']}⭐",
                callback_data=f"pro_{key}",
            )]
            for key, p in SUBSCRIPTION_PLANS.items()
        ]
    )

    await message.answer(
        "💎 <b>Pro подписка</b>\n\n"
        "Что входит:\n"
        "• 🚀 30 постов в день (вместо 3)\n"
        "• 🤖 Продвинутая модель AI\n"
        "• ✨ Без водяного знака\n"
        "• 🎨 Выбор стиля и длины\n\n"
        "Выберите план:",
        reply_markup=keyboard,
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("pro_"))
async def subscription_callback(callback_query):
    """Handle plan selection — send Stars invoice."""
    await callback_query.answer()

    user_id = callback_query.from_user.id
    if not payments_enabled():
        await callback_query.message.answer(
            "💳 Платежи временно отключены.",
            parse_mode="HTML",
        )
        return

    plan_key = callback_query.data.replace("pro_", "")
    plan = SUBSCRIPTION_PLANS.get(plan_key)
    if not plan:
        await callback_query.message.answer("❌ Неизвестный план.")
        return

    # Ensure user exists in DB
    await register_or_get_user(
        telegram_id=user_id,
        username=callback_query.from_user.username,
        first_name=callback_query.from_user.first_name,
        last_name=callback_query.from_user.last_name,
    )

    title = f"Pro подписка — {plan['label']}"
    description = f"{plan['days']} дней Pro: 30 постов/день, sonar-pro, без водяного знака"

    invoice_kwargs = dict(
        title=title,
        description=description,
        prices=[LabeledPrice(label="XTR", amount=plan["stars"])],
        provider_token="",
        payload=f"pro_{plan_key}",
        currency="XTR",
    )

    # Monthly plan uses recurring billing
    if plan_key == "month":
        invoice_kwargs["subscription_period"] = 2592000  # 30 days in seconds

    try:
        await callback_query.message.answer_invoice(**invoice_kwargs)
    except TelegramBadRequest as e:
        logger.error(f"Failed to send Stars invoice: {e}")
        await callback_query.message.answer(
            "❌ Не удалось создать счёт. Попробуйте позже.",
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error(f"Invoice error for user {user_id}: {e}", exc_info=True)
        await callback_query.message.answer(
            "❌ Ошибка при создании счёта. Попробуйте позже.",
            parse_mode="HTML",
        )


@router.pre_checkout_query()
async def pre_checkout_handler(query: PreCheckoutQuery):
    """Approve Stars pre-checkout."""
    if not payments_enabled():
        await query.answer(ok=False, error_message="Платежи временно отключены.")
        return

    logger.info(f"Pre-checkout from user {query.from_user.id}, payload={query.invoice_payload}")
    await query.answer(ok=True)


@router.message(F.successful_payment)
async def successful_payment_handler(message: Message):
    """Handle successful Stars payment — activate Pro subscription."""
    if not payments_enabled():
        await message.answer("⚠️ Платёж получен, но платежи отключены. Свяжитесь с поддержкой.")
        return

    payment = message.successful_payment
    plan_key = payment.invoice_payload.replace("pro_", "")
    plan = SUBSCRIPTION_PLANS.get(plan_key)

    if not plan:
        logger.error(f"Unknown plan in payload: {payment.invoice_payload}")
        await message.answer("⚠️ Платёж получен, но план не распознан. Свяжитесь с поддержкой.")
        return

    user_id = message.from_user.id
    logger.info(f"Successful payment from user {user_id}, plan={plan_key}")

    # Update user subscription in DB
    from sqlalchemy import select

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == user_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            # Create user if somehow missing
            user = User(
                telegram_id=user_id,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name,
            )
            session.add(user)
            await session.flush()

        now = datetime.utcnow()
        # Extend from current end if still active
        if user.subscription_end and user.subscription_end > now:
            user.subscription_end = user.subscription_end + timedelta(days=plan["days"])
        else:
            user.subscription_end = now + timedelta(days=plan["days"])

        user.is_premium = True
        user.updated_at = now

        # Record payment
        pay_record = Payment(
            user_id=user.id,
            amount=plan["stars"],
            currency="XTR",
            status=PaymentStatus.SUCCESS,
            provider="telegram_stars",
            payload={
                "plan": f"pro_{plan_key}",
                "charge_id": payment.telegram_payment_charge_id,
            },
            paid_at=now,
        )
        session.add(pay_record)
        await session.commit()
        await session.refresh(user)

    expiry_str = user.subscription_end.strftime("%d.%m.%Y")

    await message.answer(
        f"🎉 <b>Подписка Pro активирована!</b>\n\n"
        f"📋 План: {plan['label']}\n"
        f"📅 Действует до: {expiry_str}\n\n"
        f"Что доступно:\n"
        f"• 30 постов в день\n"
        f"• Продвинутая модель AI\n"
        f"• Без водяного знака\n"
        f"• Выбор стиля и длины",
        parse_mode="HTML",
    )


@router.message(Command("status"))
async def status_command(message: Message):
    """Show subscription status with usage info."""
    user_id = message.from_user.id
    user = await get_user(user_id)

    user_is_premium = await check_is_premium(user_id) if user else False
    today_count = await get_today_post_count(user_id)
    total_count = await get_total_post_count(user_id)

    if user_is_premium and user and user.subscription_end:
        expiry_str = user.subscription_end.strftime("%d.%m.%Y")
        daily_limit = PRO_DAILY_LIMIT
        tariff = f"Pro (до {expiry_str})"
        model = "sonar-pro"
    else:
        daily_limit = FREE_DAILY_LIMIT
        tariff = "Free"
        model = "sonar-small"

    await message.answer(
        f"📊 <b>Ваш статус:</b>\n"
        f"├ Тариф: <b>{tariff}</b>\n"
        f"├ Постов сегодня: <b>{today_count}/{daily_limit}</b>\n"
        f"├ Модель: <b>{model}</b>\n"
        f"└ Всего создано: <b>{total_count}</b> постов",
        parse_mode="HTML",
    )
