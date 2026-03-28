"""Хэндлеры автопостинга: FSM-настройка, оплата Stars, управление подписками."""

from aiogram import Router, F, types, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    LabeledPrice,
)

from database.database import get_session
from services.autopost_service import (
    AUTOPOST_PLANS,
    FREQUENCY_LABELS,
    create_autopost_subscription,
    get_active_subscriptions,
    cancel_subscription,
    update_topic,
    count_active_subscriptions_for_channel,
)
from logger_config import logger

router = Router()

# МСК = UTC+3
MSK_OFFSET = 3


class AutopostSetup(StatesGroup):
    waiting_topic = State()
    waiting_frequency = State()
    waiting_time = State()
    waiting_custom_time = State()
    waiting_channel = State()
    waiting_confirmation = State()
    editing_topic = State()


def _msk_to_utc(msk_hour: int) -> int:
    return (msk_hour - MSK_OFFSET) % 24


def _utc_to_msk(utc_hour: int) -> int:
    return (utc_hour + MSK_OFFSET) % 24


# ==================== FSM: Настройка автопостинга ====================


@router.message(F.text == "📬 Автопостинг")
async def cmd_autopost(message: types.Message, state: FSMContext):
    await state.clear()
    await state.set_state(AutopostSetup.waiting_topic)
    await message.answer(
        "📬 <b>Настройка автопостинга</b>\n\n"
        "Я буду генерировать посты по вашей теме и публиковать их "
        "в ваш Telegram-канал по расписанию.\n\n"
        "📝 <b>Введите тему постов:</b>\n"
        "<i>(например: «SMM продвижение», «здоровое питание», «криптовалюты»)</i>"
    )


@router.message(AutopostSetup.waiting_topic)
async def got_topic(message: types.Message, state: FSMContext):
    topic = message.text.strip()
    if len(topic) > 200:
        await message.answer("❌ Тема слишком длинная. Максимум 200 символов.")
        return
    if len(topic) < 2:
        await message.answer("❌ Тема слишком короткая. Минимум 2 символа.")
        return

    await state.update_data(topic=topic)
    await state.set_state(AutopostSetup.waiting_frequency)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="1 раз в день", callback_data="autopost_freq:daily"),
            InlineKeyboardButton(text="2 раза в день", callback_data="autopost_freq:twice_daily"),
        ],
        [
            InlineKeyboardButton(text="Каждые 6 часов", callback_data="autopost_freq:every_6h"),
            InlineKeyboardButton(text="Раз в неделю", callback_data="autopost_freq:weekly"),
        ],
    ])

    await message.answer(
        f"Тема: <b>{topic}</b>\n\n"
        "⏰ <b>Как часто отправлять посты?</b>",
        reply_markup=kb,
    )


@router.callback_query(AutopostSetup.waiting_frequency, F.data.startswith("autopost_freq:"))
async def got_frequency(call: types.CallbackQuery, state: FSMContext):
    frequency = call.data.split(":")[1]
    await state.update_data(frequency=frequency)
    await call.answer()

    if frequency == "every_6h":
        # Фиксированные слоты для every_6h: 00/06/12/18 UTC → 03/09/15/21 МСК
        await state.update_data(send_hour_utc=0, send_hour_local=3)
        await state.set_state(AutopostSetup.waiting_channel)
        await call.message.edit_text(
            f"⏰ Время: <b>03:00, 09:00, 15:00, 21:00 МСК</b>\n\n"
            "📢 <b>Укажите канал для публикации:</b>\n\n"
            "Отправьте @username канала.\n\n"
            "⚠️ Бот должен быть добавлен как администратор канала "
            "с правом публикации."
        )
        return

    if frequency == "twice_daily":
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="09:00 и 18:00 МСК", callback_data="autopost_time:9")],
            [InlineKeyboardButton(text="10:00 и 20:00 МСК", callback_data="autopost_time:10")],
            [InlineKeyboardButton(text="08:00 и 14:00 МСК", callback_data="autopost_time:8")],
            [InlineKeyboardButton(text="Другое время", callback_data="autopost_time:custom")],
        ])
    else:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="09:00", callback_data="autopost_time:9"),
                InlineKeyboardButton(text="12:00", callback_data="autopost_time:12"),
                InlineKeyboardButton(text="15:00", callback_data="autopost_time:15"),
            ],
            [
                InlineKeyboardButton(text="18:00", callback_data="autopost_time:18"),
                InlineKeyboardButton(text="21:00", callback_data="autopost_time:21"),
            ],
            [InlineKeyboardButton(text="Другое время", callback_data="autopost_time:custom")],
        ])

    await state.set_state(AutopostSetup.waiting_time)
    await call.message.edit_text(
        "🕐 <b>В какое время публиковать? (МСК)</b>",
        reply_markup=kb,
    )


@router.callback_query(AutopostSetup.waiting_time, F.data.startswith("autopost_time:"))
async def got_time(call: types.CallbackQuery, state: FSMContext):
    value = call.data.split(":")[1]
    await call.answer()

    if value == "custom":
        await state.set_state(AutopostSetup.waiting_custom_time)
        data = await state.get_data()
        if data.get("frequency") == "twice_daily":
            await call.message.edit_text(
                "🕐 Введите два часа через запятую (МСК, 0-23):\n"
                "<i>Например: 9,18</i>"
            )
        else:
            await call.message.edit_text(
                "🕐 Введите час публикации (МСК, 0-23):\n"
                "<i>Например: 14</i>"
            )
        return

    msk_hour = int(value)
    utc_hour = _msk_to_utc(msk_hour)
    await state.update_data(send_hour_utc=utc_hour, send_hour_local=msk_hour)
    await state.set_state(AutopostSetup.waiting_channel)

    data = await state.get_data()
    if data.get("frequency") == "twice_daily":
        second_msk = (msk_hour + 12) % 24
        time_str = f"{msk_hour:02d}:00 и {second_msk:02d}:00 МСК"
    else:
        time_str = f"{msk_hour:02d}:00 МСК"

    await call.message.edit_text(
        f"⏰ Время: <b>{time_str}</b>\n\n"
        "📢 <b>Укажите канал для публикации:</b>\n\n"
        "Отправьте @username канала.\n\n"
        "⚠️ Бот должен быть добавлен как администратор канала "
        "с правом публикации."
    )


@router.message(AutopostSetup.waiting_custom_time)
async def got_custom_time(message: types.Message, state: FSMContext):
    data = await state.get_data()
    text = message.text.strip()

    if data.get("frequency") == "twice_daily":
        parts = [p.strip() for p in text.replace(" ", ",").split(",") if p.strip()]
        if len(parts) != 2:
            await message.answer("❌ Введите два числа через запятую (0-23). Например: 9,18")
            return
        try:
            h1, h2 = int(parts[0]), int(parts[1])
            if not (0 <= h1 <= 23 and 0 <= h2 <= 23):
                raise ValueError
        except ValueError:
            await message.answer("❌ Введите числа от 0 до 23.")
            return
        msk_hour = h1
    else:
        try:
            msk_hour = int(text)
            if not 0 <= msk_hour <= 23:
                raise ValueError
        except ValueError:
            await message.answer("❌ Введите число от 0 до 23.")
            return

    utc_hour = _msk_to_utc(msk_hour)
    await state.update_data(send_hour_utc=utc_hour, send_hour_local=msk_hour)
    await state.set_state(AutopostSetup.waiting_channel)

    if data.get("frequency") == "twice_daily":
        second_msk = (msk_hour + 12) % 24
        time_str = f"{msk_hour:02d}:00 и {second_msk:02d}:00 МСК"
    else:
        time_str = f"{msk_hour:02d}:00 МСК"

    await message.answer(
        f"⏰ Время: <b>{time_str}</b>\n\n"
        "📢 <b>Укажите канал для публикации:</b>\n\n"
        "Отправьте @username канала.\n\n"
        "⚠️ Бот должен быть добавлен как администратор канала "
        "с правом публикации."
    )


@router.message(AutopostSetup.waiting_channel)
async def got_channel(message: types.Message, state: FSMContext, bot: Bot):
    channel_input = message.text.strip()

    if not channel_input.startswith("@"):
        channel_input = "@" + channel_input

    # Проверяем канал
    try:
        chat = await bot.get_chat(channel_input)
    except Exception:
        await message.answer(
            f"❌ Канал <b>{channel_input}</b> не найден.\n\n"
            "Убедитесь, что:\n"
            "1. Канал существует\n"
            "2. Username введён правильно\n\n"
            "Попробуйте снова: отправьте @username канала."
        )
        return

    # Проверяем, является ли бот администратором
    try:
        bot_member = await bot.get_chat_member(chat.id, bot.id)
        if bot_member.status not in ("administrator", "creator"):
            raise ValueError("not admin")
        if not getattr(bot_member, "can_post_messages", False):
            raise ValueError("no post rights")
    except ValueError:
        await message.answer(
            f"❌ Бот не является администратором канала {channel_input}.\n\n"
            "Добавьте бота как администратора канала:\n"
            "1. Откройте настройки канала\n"
            "2. «Администраторы» → «Добавить администратора»\n"
            "3. Найдите бота\n"
            "4. Включите «Публикация сообщений»\n\n"
            "Попробуйте снова: отправьте @username канала."
        )
        return
    except Exception:
        await message.answer(
            f"❌ Не удалось проверить права бота в канале {channel_input}.\n\n"
            "Убедитесь, что бот добавлен как администратор с правом публикации.\n\n"
            "Попробуйте снова: отправьте @username канала."
        )
        return

    channel_id = str(chat.id)
    channel_title = chat.title or channel_input
    await state.update_data(
        channel_id=channel_id,
        channel_username=channel_input,
        channel_title=channel_title,
    )
    await state.set_state(AutopostSetup.waiting_confirmation)

    data = await state.get_data()
    topic = data["topic"]
    frequency = data["frequency"]
    freq_label = FREQUENCY_LABELS.get(frequency, frequency)
    msk_hour = data.get("send_hour_local", 9)

    if frequency == "twice_daily":
        second_msk = (msk_hour + 12) % 24
        time_str = f"{msk_hour:02d}:00 и {second_msk:02d}:00 МСК"
    elif frequency == "every_6h":
        time_str = "03:00, 09:00, 15:00, 21:00 МСК"
    else:
        time_str = f"{msk_hour:02d}:00 МСК"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"150 ⭐ — Месяц (1 канал)",
            callback_data="autopost_plan:month",
        )],
        [InlineKeyboardButton(
            text=f"750 ⭐ — Полгода (до 3 каналов)",
            callback_data="autopost_plan:half_year",
        )],
        [InlineKeyboardButton(
            text=f"1200 ⭐ — Год (до 5 каналов)",
            callback_data="autopost_plan:year",
        )],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="autopost_cancel_setup")],
    ])

    await message.answer(
        "📋 <b>Автопостинг настроен:</b>\n\n"
        f"📝 Тема: <b>{topic}</b>\n"
        f"⏰ Частота: <b>{freq_label}</b>\n"
        f"🕐 Время: <b>{time_str}</b>\n"
        f"📢 Канал: <b>{channel_title}</b> ({channel_input})\n\n"
        "💳 <b>Выберите план:</b>",
        reply_markup=kb,
    )


@router.callback_query(F.data == "autopost_cancel_setup")
async def cancel_setup(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await call.answer()
    await call.message.edit_text("❌ Настройка автопостинга отменена.")


# ==================== Оплата Stars ====================


@router.callback_query(AutopostSetup.waiting_confirmation, F.data.startswith("autopost_plan:"))
async def got_plan(call: types.CallbackQuery, state: FSMContext, bot: Bot):
    plan_type = call.data.split(":")[1]
    plan = AUTOPOST_PLANS.get(plan_type)
    if not plan:
        await call.answer("❌ Неизвестный тариф", show_alert=True)
        return

    # Проверяем лимит каналов для пользователя
    async with get_session() as session:
        current_count = await count_active_subscriptions_for_channel(
            session, call.from_user.id
        )
    if current_count >= plan["max_channels"]:
        await call.answer(
            f"❌ Тариф «{plan['label']}» позволяет до {plan['max_channels']} "
            f"каналов. У вас уже {current_count}.",
            show_alert=True,
        )
        return

    await state.update_data(plan_type=plan_type)
    await call.answer()

    prices = [LabeledPrice(label=f"Автопостинг — {plan['label']}", amount=plan["stars"])]

    invoice_kwargs = dict(
        chat_id=call.from_user.id,
        title=f"Автопостинг — {plan['label']}",
        description=plan["description"],
        payload=f"autopost:{plan_type}",
        currency="XTR",
        prices=prices,
    )

    # Месячный тариф — рекуррентный (subscription_period = 30 дней в секундах)
    if plan_type == "month":
        invoice_kwargs["subscription_period"] = 2592000

    await bot.send_invoice(**invoice_kwargs)


@router.pre_checkout_query(F.invoice_payload.startswith("autopost:"))
async def pre_checkout_autopost(query: types.PreCheckoutQuery):
    await query.answer(ok=True)


@router.message(F.successful_payment)
async def successful_payment_autopost(message: types.Message, state: FSMContext, bot: Bot):
    payment = message.successful_payment
    if not payment.invoice_payload.startswith("autopost:"):
        return  # не наш платёж, пропустить для другого обработчика

    plan_type = payment.invoice_payload.split(":")[1]
    data = await state.get_data()

    if not data.get("topic"):
        # Повторный платёж (рекуррентный) — обрабатываем отдельно
        logger.info(
            f"Recurring autopost payment from {message.from_user.id}, "
            f"charge_id={payment.telegram_payment_charge_id}"
        )
        return

    plan = AUTOPOST_PLANS[plan_type]

    async with get_session() as session:
        sub = await create_autopost_subscription(
            session=session,
            telegram_id=message.from_user.id,
            channel_id=data["channel_id"],
            channel_title=data.get("channel_title", ""),
            topic=data["topic"],
            frequency=data["frequency"],
            send_hour_utc=data["send_hour_utc"],
            send_hour_local=data.get("send_hour_local", 9),
            plan_type=plan_type,
            stars_paid=plan["stars"],
            telegram_charge_id=payment.telegram_payment_charge_id,
        )

    freq_label = FREQUENCY_LABELS.get(data["frequency"], data["frequency"])
    msk_hour = data.get("send_hour_local", 9)

    await message.answer(
        "✅ <b>Автопостинг активирован!</b>\n\n"
        f"📝 Тема: <b>{data['topic']}</b>\n"
        f"⏰ Частота: <b>{freq_label}</b>\n"
        f"🕐 Время: <b>{msk_hour:02d}:00 МСК</b>\n"
        f"📢 Канал: <b>{data.get('channel_title', data['channel_id'])}</b>\n"
        f"💳 Тариф: <b>{plan['label']}</b> ({plan['stars']} ⭐)\n"
        f"📅 Действует до: <b>{sub.expires_at.strftime('%d.%m.%Y')}</b>\n\n"
        "Бот будет автоматически генерировать и публиковать посты "
        "по расписанию.\n\n"
        "📌 Управление: /my_autoposts"
    )
    await state.clear()


# ==================== /my_autoposts ====================


@router.message(Command("my_autoposts"))
async def cmd_my_autoposts(message: types.Message):
    async with get_session() as session:
        subs = await get_active_subscriptions(session, message.from_user.id)

    if not subs:
        await message.answer(
            "📭 У вас нет активных автопостов.\n"
            "Нажмите «📬 Автопостинг» для настройки."
        )
        return

    text = "📬 <b>Ваши автопостинги:</b>\n\n"
    buttons = []
    for i, sub in enumerate(subs, 1):
        freq_label = FREQUENCY_LABELS.get(sub.frequency, sub.frequency)
        msk_hour = sub.send_hour_local

        if sub.frequency == "twice_daily":
            second_msk = (msk_hour + 12) % 24
            time_str = f"{msk_hour:02d}:00 и {second_msk:02d}:00 МСК"
        elif sub.frequency == "every_6h":
            time_str = f"каждые 6ч"
        else:
            time_str = f"{msk_hour:02d}:00 МСК"

        expires_str = sub.expires_at.strftime("%d.%m.%Y")
        channel_display = sub.channel_title or sub.channel_id

        text += (
            f"{i}. 📝 <b>{sub.topic}</b>\n"
            f"   📢 {channel_display}\n"
            f"   ⏰ {freq_label} в {time_str}\n"
            f"   📅 До: {expires_str}\n"
            f"   📊 Опубликовано: {sub.posts_generated} постов\n\n"
        )
        buttons.append([
            InlineKeyboardButton(
                text=f"✏️ Тема «{sub.topic[:20]}»",
                callback_data=f"autopost_edit:{sub.id}",
            ),
            InlineKeyboardButton(
                text=f"❌ Отменить",
                callback_data=f"autopost_cancel:{sub.id}",
            ),
        ])

    kb = InlineKeyboardMarkup(inline_keyboard=buttons) if buttons else None
    await message.answer(text, reply_markup=kb)


# ==================== Редактирование темы ====================


@router.callback_query(F.data.startswith("autopost_edit:"))
async def cb_edit_topic(call: types.CallbackQuery, state: FSMContext):
    sub_id = int(call.data.split(":")[1])
    await state.set_state(AutopostSetup.editing_topic)
    await state.update_data(editing_sub_id=sub_id)
    await call.answer()
    await call.message.answer("📝 Введите новую тему для автопостинга:")


@router.message(AutopostSetup.editing_topic)
async def got_new_topic(message: types.Message, state: FSMContext):
    new_topic = message.text.strip()
    if len(new_topic) > 200:
        await message.answer("❌ Тема слишком длинная. Максимум 200 символов.")
        return
    if len(new_topic) < 2:
        await message.answer("❌ Тема слишком короткая. Минимум 2 символа.")
        return

    data = await state.get_data()
    sub_id = data.get("editing_sub_id")

    async with get_session() as session:
        ok = await update_topic(session, sub_id, message.from_user.id, new_topic)

    if ok:
        await message.answer(f"✅ Тема обновлена: <b>{new_topic}</b>")
    else:
        await message.answer("❌ Не удалось обновить тему. Подписка не найдена.")

    await state.clear()


# ==================== Отмена подписки ====================


@router.callback_query(F.data.startswith("autopost_cancel:"))
async def cb_cancel_sub(call: types.CallbackQuery):
    sub_id = int(call.data.split(":")[1])

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ Да, отменить",
                callback_data=f"autopost_confirm_cancel:{sub_id}",
            ),
            InlineKeyboardButton(
                text="❌ Нет",
                callback_data="autopost_keep",
            ),
        ]
    ])

    await call.answer()
    await call.message.answer(
        "⚠️ <b>Вы уверены?</b>\n\n"
        "Автопостинг будет остановлен. Доступ сохранится до конца оплаченного периода.",
        reply_markup=kb,
    )


@router.callback_query(F.data.startswith("autopost_confirm_cancel:"))
async def cb_confirm_cancel(call: types.CallbackQuery):
    sub_id = int(call.data.split(":")[1])

    async with get_session() as session:
        ok = await cancel_subscription(session, sub_id, call.from_user.id)

    if ok:
        await call.message.edit_text("✅ Автопостинг отменён.")
    else:
        await call.answer("❌ Подписка не найдена.", show_alert=True)


@router.callback_query(F.data == "autopost_keep")
async def cb_keep_sub(call: types.CallbackQuery):
    await call.answer()
    await call.message.edit_text("👍 Автопостинг продолжает работать.")
