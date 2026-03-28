"""Хэндлеры ежедневных подписок на тему."""
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from database.database import get_session
from services.subscription_topic_service import (
    add_subscription,
    get_user_subscriptions,
    cancel_subscription,
)

router = Router()


class SubscribeFSM(StatesGroup):
    waiting_topic = State()
    waiting_hour = State()


@router.message(Command("subscribe"))
@router.message(F.text == "📬 Подписки")
async def cmd_subscribe(message: types.Message, state: FSMContext):
    await state.set_state(SubscribeFSM.waiting_topic)
    await message.answer(
        "📬 <b>Подписка на ежедневные посты</b>\n\n"
        "Напишите тему, по которой хотите получать пост каждый день.\n"
        "<i>Например: огурцы, SMM, криптовалюта</i>"
    )


@router.message(SubscribeFSM.waiting_topic)
async def got_topic(message: types.Message, state: FSMContext):
    topic = message.text.strip()
    if len(topic) > 200:
        await message.answer("❌ Тема слишком длинная. Максимум 200 символов.")
        return
    await state.update_data(topic=topic)
    await state.set_state(SubscribeFSM.waiting_hour)
    await message.answer(
        f"⏰ <b>В какое время присылать пост?</b>\n\n"
        f"Введите час по UTC (0–23).\n"
        f"<i>Например: 8 = 08:00 UTC (11:00 МСК)</i>"
    )


@router.message(SubscribeFSM.waiting_hour)
async def got_hour(message: types.Message, state: FSMContext):
    try:
        hour = int(message.text.strip())
        if not 0 <= hour <= 23:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введите число от 0 до 23.")
        return

    data = await state.get_data()
    topic = data["topic"]

    async with get_session() as session:
        sub, error = await add_subscription(
            session, message.from_user.id, topic, send_hour_utc=hour
        )

    if error:
        await message.answer(f"❌ {error}")
    else:
        await message.answer(
            f"✅ <b>Подписка оформлена!</b>\n\n"
            f"📌 Тема: <b>{topic}</b>\n"
            f"⏰ Время: <b>{hour:02d}:00 UTC</b>\n\n"
            f"Каждый день в это время я буду присылать вам готовый пост по этой теме.\n\n"
            f"📌 Управлять подписками: /my\_subscriptions"
        )
    await state.clear()


@router.message(Command("my_subscriptions"))
async def cmd_my_subscriptions(message: types.Message):
    async with get_session() as session:
        subs = await get_user_subscriptions(session, message.from_user.id)

    if not subs:
        await message.answer(
            "📭 У вас нет активных подписок.\n"
            "Используйте /subscribe или кнопку 📬 Подписки."
        )
        return

    text = "📋 <b>Ваши подписки:</b>\n\n"
    buttons = []
    for sub in subs:
        text += f"• <b>{sub.topic}</b> — {sub.send_hour_utc:02d}:00 UTC\n"
        buttons.append([
            InlineKeyboardButton(
                text=f"❌ Отменить \u00ab{sub.topic[:25]}\u00bb",
                callback_data=f"unsub:{sub.id}",
            )
        ])

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith("unsub:"))
async def cb_unsubscribe(call: types.CallbackQuery):
    sub_id = int(call.data.split(":")[1])
    async with get_session() as session:
        ok = await cancel_subscription(session, sub_id, call.from_user.id)
    if ok:
        await call.message.edit_text("✅ Подписка отменена.")
    else:
        await call.answer("❌ Подписка не найдена.", show_alert=True)
