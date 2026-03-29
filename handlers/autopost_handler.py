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

MSK_OFFSET = 3


class AutopostSetup(StatesGroup):
    # ШАГ 0: выбор способа доставки
    waiting_delivery_method = State()
    # ШАГ 0b: ввод токена своего бота (только для метода 2)
    waiting_user_bot_token = State()
    # ШАГ 1-5: общие для обоих методов
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


# ==================== ШАГ 0: Выбор способа доставки ====================


@router.message(F.text == "📬 Автопостинг")
async def cmd_autopost(message: types.Message, state: FSMContext):
    await state.clear()
    await state.set_state(AutopostSetup.waiting_delivery_method)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🤝 Добавить бота в мой канал",
            callback_data="autopost_delivery:shared",
        )],
        [InlineKeyboardButton(
            text="🔑 Использовать свой бот",
            callback_data="autopost_delivery:own_bot",
        )],
    ])

    await message.answer(
        "📬 <b>Автопостинг — выберите способ публикации:</b>\n\n"
        "🤝 <b>Добавить бота в мой канал</b>\n"
        "Быстрый старт. Вы добавляете этого бота администратором "
        "в свой канал — он сам публикует посты.\n\n"
        "🔑 <b>Использовать свой бот</b>\n"
        "Вы создаёте личного бота через @BotFather, добавляете "
        "его в канал. Никакой сторонний бот не получает прав администратора.",
        reply_markup=kb,
    )


@router.callback_query(
    AutopostSetup.waiting_delivery_method,
    F.data.startswith("autopost_delivery:"),
)
async def got_delivery_method(call: types.CallbackQuery, state: FSMContext):
    method = call.data.split(":")[1]
    await state.update_data(delivery_method=method)
    await call.answer()

    if method == "own_bot":
        await state.set_state(AutopostSetup.waiting_user_bot_token)
        await call.message.edit_text(
            "🔑 <b>Шаг 1 из 6 — Создайте своего бота</b>\n\n"
            "1. Откройте @BotFather в Telegram\n"
            "2. Отправьте команду /newbot\n"
            "3. Придумайте имя и username для бота\n"
            "4. BotFather выдаст вам токен вида:\n"
            "   <code>1234567890:AABBccDDeeFFggHH...</code>\n\n"
            "📋 <b>Скопируйте и отправьте токен сюда:</b>\n"
            "<i>Токен хранится в зашифрованном виде и используется "
            "только для публикации постов в ваш канал.</i>"
        )
    else:
        # shared — сразу к теме
        await state.set_state(AutopostSetup.waiting_topic)
        await call.message.edit_text(
            "🤝 <b>Шаг 1 из 5 — Тема постов</b>\n\n"
            "📝 <b>Введите тему для автопостинга:</b>\n"
            "<i>Например: «SMM продвижение», «здоровое питание», «криптовалюты»</i>\n\n"
            "💡 Позже вы добавите этого бота администратором в свой канал."
        )


# ==================== ШАГ 1b (только own_bot): Токен ====================


@router.message(AutopostSetup.waiting_user_bot_token)
async def got_user_bot_token(message: types.Message, state: FSMContext, bot: Bot):
    token = message.text.strip()

    # Базовая проверка формата
    import re
    if not re.match(r"^\d+:[A-Za-z0-9_-]{35,}$", token):
        await message.answer(
            "❌ Токен выглядит неправильно.\n\n"
            "Токен должен быть в формате:\n"
            "<code>1234567890:AABBccDDeeFFggHHiiJJ...</code>\n\n"
            "Скопируйте токен из @BotFather и отправьте снова."
        )
        return

    # Проверяем токен через getMe
    try:
        user_bot = Bot(token=token)
        bot_info = await user_bot.get_me()
        await user_bot.session.close()
    except Exception:
        await message.answer(
            "❌ Не удалось подключиться к боту с этим токеном.\n\n"
            "Проверьте, что:\n"
            "• Токен скопирован полностью\n"
            "• Бот не заблокирован\n\n"
            "Попробуйте снова — отправьте токен."
        )
        return

    # Удаляем сообщение с токеном из чата для безопасности
    try:
        await message.delete()
    except Exception:
        pass

    await state.update_data(user_bot_token=token, user_bot_username=bot_info.username)
    await state.set_state(AutopostSetup.waiting_topic)

    await message.answer(
        f"✅ <b>Бот @{bot_info.username} подключён!</b>\n\n"
        "🔑 <b>Шаг 2 из 6 — Тема постов</b>\n\n"
        "📝 <b>Введите тему для автопостинга:</b>\n"
        "<i>Например: «SMM продвижение», «здоровое питание», «криптовалюты»</i>"
    )


# ==================== ШАГ 2: Тема ====================


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

    data = await state.get_data()
    method = data.get("delivery_method", "shared")
    step = "3 из 6" if method == "own_bot" else "2 из 5"

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
        f"⏰ <b>Шаг {step} — Частота публикаций</b>\n\n"
        f"Тема: <b>{topic}</b>\n\n"
        "<b>Как часто публиковать посты?</b>",
        reply_markup=kb,
    )


# ==================== ШАГ 3: Частота ====================


@router.callback_query(AutopostSetup.waiting_frequency, F.data.startswith("autopost_freq:"))
async def got_frequency(call: types.CallbackQuery, state: FSMContext):
    frequency = call.data.split(":")[1]
    await state.update_data(frequency=frequency)
    await call.answer()

    data = await state.get_data()
    method = data.get("delivery_method", "shared")
    step = "4 из 6" if method == "own_bot" else "3 из 5"

    if frequency == "every_6h":
        await state.update_data(send_hour_utc=0, send_hour_local=3)
        await state.set_state(AutopostSetup.waiting_channel)
        await _ask_channel(call.message, state, step_override=step)
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
        f"🕐 <b>Шаг {step} — Время публикации (МСК)</b>\n\n"
        "<b>В какое время публиковать?</b>",
        reply_markup=kb,
    )


# ==================== ШАГ 4: Время ====================


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
    method = data.get("delivery_method", "shared")
    step = "5 из 6" if method == "own_bot" else "4 из 5"
    await _ask_channel(call.message, state, step_override=step)


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

    method = data.get("delivery_method", "shared")
    step = "5 из 6" if method == "own_bot" else "4 из 5"
    await _ask_channel(message, state, step_override=step)


async def _ask_channel(target, state: FSMContext, step_override: str = None):
    """Отправить инструкцию по добавлению канала в зависимости от метода."""
    data = await state.get_data()
    method = data.get("delivery_method", "shared")
    step = step_override or ("5 из 6" if method == "own_bot" else "4 из 5")

    if method == "own_bot":
        bot_username = data.get("user_bot_username", "ваш бот")
        instruction = (
            f"📢 <b>Шаг {step} — Подключите канал</b>\n\n"
            f"Перед тем как продолжить, добавьте <b>@{bot_username}</b> "
            f"администратором вашего канала:\n\n"
            "1. Откройте настройки вашего канала\n"
            "2. «Администраторы» → «Добавить администратора»\n"
            f"3. Найдите @{bot_username}\n"
            "4. Включите <b>«Публикация сообщений»</b>\n"
            "5. Сохраните\n\n"
            "✅ Готово? Отправьте @username вашего канала:"
        )
    else:
        instruction = (
            f"📢 <b>Шаг {step} — Подключите канал</b>\n\n"
            "Добавьте этого бота администратором вашего канала:\n\n"
            "1. Откройте настройки вашего канала\n"
            "2. «Администраторы» → «Добавить администратора»\n"
            "3. Найдите этого бота\n"
            "4. Включите <b>«Публикация сообщений»</b>\n"
            "5. Сохраните\n\n"
            "✅ Готово? Отправьте @username вашего канала:"
        )

    # target может быть Message или message из CallbackQuery
    if hasattr(target, 'edit_text'):
        await target.edit_text(instruction)
    else:
        await target.answer(instruction)


# ==================== ШАГ 5: Канал ====================


@router.message(AutopostSetup.waiting_channel)
async def got_channel(message: types.Message, state: FSMContext, bot: Bot):
    channel_input = message.text.strip()
    if not channel_input.startswith("@"):
        channel_input = "@" + channel_input

    data = await state.get_data()
    method = data.get("delivery_method", "shared")

    # Выбираем бота для проверки
    if method == "own_bot" and data.get("user_bot_token"):
        check_bot = Bot(token=data["user_bot_token"])
        should_close = True
    else:
        check_bot = bot
        should_close = False

    try:
        chat = await check_bot.get_chat(channel_input)
    except Exception:
        if should_close:
            await check_bot.session.close()
        bot_name = f"@{data.get('user_bot_username', 'бот')}" if method == "own_bot" else "бот"
        await message.answer(
            f"❌ Канал <b>{channel_input}</b> не найден.\n\n"
            f"Убедитесь, что {bot_name} добавлен как администратор, "
            "и канал существует.\n\nОтправьте @username канала снова."
        )
        return

    try:
        member = await check_bot.get_chat_member(chat.id, (await check_bot.get_me()).id)
        if member.status not in ("administrator", "creator"):
            raise ValueError("not admin")
        if not getattr(member, "can_post_messages", False):
            raise ValueError("no post rights")
    except ValueError as e:
        if should_close:
            await check_bot.session.close()
        bot_name = f"@{data.get('user_bot_username', 'бот')}" if method == "own_bot" else "бот"
        await message.answer(
            f"❌ {bot_name} не является администратором канала "
            f"{channel_input} или не имеет права публикации.\n\n"
            "Проверьте настройки и отправьте @username канала снова."
        )
        return
    except Exception:
        if should_close:
            await check_bot.session.close()
        await message.answer(
            "❌ Не удалось проверить права. Убедитесь что бот — "
            "администратор канала с правом публикации.\n\n"
            "Отправьте @username канала снова."
        )
        return
    finally:
        if should_close:
            try:
                await check_bot.session.close()
            except Exception:
                pass

    channel_id = str(chat.id)
    channel_title = chat.title or channel_input
    await state.update_data(
        channel_id=channel_id,
        channel_username=channel_input,
        channel_title=channel_title,
    )
    await state.set_state(AutopostSetup.waiting_confirmation)

    step = "6 из 6" if method == "own_bot" else "5 из 5"
    freq_label = FREQUENCY_LABELS.get(data["frequency"], data["frequency"])
    msk_hour = data.get("send_hour_local", 9)

    if data["frequency"] == "twice_daily":
        second_msk = (msk_hour + 12) % 24
        time_str = f"{msk_hour:02d}:00 и {second_msk:02d}:00 МСК"
    elif data["frequency"] == "every_6h":
        time_str = "03:00, 09:00, 15:00, 21:00 МСК"
    else:
        time_str = f"{msk_hour:02d}:00 МСК"

    method_label = (
        f"🔑 Ваш бот @{data.get('user_bot_username')}"
        if method == "own_bot"
        else "🤝 Этот бот"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="150 ⭐ — Месяц (1 канал)",
            callback_data="autopost_plan:month",
        )],
        [InlineKeyboardButton(
            text="750 ⭐ — Полгода (до 3 каналов)",
            callback_data="autopost_plan:half_year",
        )],
        [InlineKeyboardButton(
            text="1200 ⭐ — Год (до 5 каналов)",
            callback_data="autopost_plan:year",
        )],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="autopost_cancel_setup")],
    ])

    await message.answer(
        f"✅ <b>Шаг {step} — Подтверждение</b>\n\n"
        "📋 <b>Параметры автопостинга:</b>\n"
        f"📝 Тема: <b>{data['topic']}</b>\n"
        f"⏰ Частота: <b>{freq_label}</b>\n"
        f"🕐 Время: <b>{time_str}</b>\n"
        f"📢 Канал: <b>{channel_title}</b> ({channel_input})\n"
        f"🤖 Публикует: <b>{method_label}</b>\n\n"
        "💳 <b>Выберите тарифный план:</b>",
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
        return

    plan_type = payment.invoice_payload.split(":")[1]
    data = await state.get_data()

    if not data.get("topic"):
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
            user_bot_token=data.get("user_bot_token"),
        )

    freq_label = FREQUENCY_LABELS.get(data["frequency"], data["frequency"])
    msk_hour = data.get("send_hour_local", 9)
    method = data.get("delivery_method", "shared")
    method_label = (
        f"🔑 Ваш бот @{data.get('user_bot_username')}"
        if method == "own_bot"
        else "🤝 Этот бот"
    )

    await message.answer(
        "✅ <b>Автопостинг активирован!</b>\n\n"
        f"📝 Тема: <b>{data['topic']}</b>\n"
        f"⏰ Частота: <b>{freq_label}</b>\n"
        f"🕐 Время: <b>{msk_hour:02d}:00 МСК</b>\n"
        f"📢 Канал: <b>{data.get('channel_title', data['channel_id'])}</b>\n"
        f"🤖 Публикует: <b>{method_label}</b>\n"
        f"💳 Тариф: <b>{plan['label']}</b> ({plan['stars']} ⭐)\n"
        f"📅 Действует до: <b>{sub.expires_at.strftime('%d.%m.%Y')}</b>\n\n"
        "Бот будет автоматически генерировать и публиковать посты по расписанию.\n\n"
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
            time_str = "каждые 6ч"
        else:
            time_str = f"{msk_hour:02d}:00 МСК"

        expires_str = sub.expires_at.strftime("%d.%m.%Y")
        channel_display = sub.channel_title or sub.channel_id
        method_icon = "🔑" if getattr(sub, "user_bot_token", None) else "🤝"

        text += (
            f"{i}. 📝 <b>{sub.topic}</b>\n"
            f"   📢 {channel_display} {method_icon}\n"
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
                text="❌ Отменить",
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
