"""
Error Notification Middleware.

Perехватывает все необработанные исключения и отправляет
администратору подробное уведомление прямо в Telegram.
"""

import html
import traceback
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update

from logger_config import logger


class ErrorNotificationMiddleware(BaseMiddleware):
    """
    Middleware, который ловит любое необработанное исключение
    и отправляет детальный отчёт администратору в Telegram.
    """

    def __init__(self, admin_id: int, bot):
        self.admin_id = admin_id
        self.bot = bot
        super().__init__()

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        try:
            return await handler(event, data)
        except Exception as exc:
            # Не отправляем уведомление если ошибка произошла у самого администратора
            # (чтобы не зациклиться)
            try:
                user_id = None
                update_id = None
                if isinstance(event, Update):
                    update_id = event.update_id
                    if event.message and event.message.from_user:
                        user_id = event.message.from_user.id
                    elif event.callback_query and event.callback_query.from_user:
                        user_id = event.callback_query.from_user.id

                tb = traceback.format_exc()
                # Обрезаем трейсбек до 3000 символов чтобы влезть в лимит Telegram
                if len(tb) > 3000:
                    tb = "..." + tb[-3000:]

                error_type = type(exc).__name__
                error_msg = str(exc)[:300]

                text = (
                    f"🚨 <b>ОШИБКА В БОТЕ</b>\n\n"
                    f"❌ <b>{html.escape(error_type)}:</b>\n"
                    f"<code>{html.escape(error_msg)}</code>\n\n"
                    f"👤 User ID: <code>{user_id or 'неизвестно'}</code>\n"
                    f"🔁 Update ID: <code>{update_id or 'неизвестно'}</code>\n\n"
                    f"📋 <b>Traceback:</b>\n"
                    f"<pre>{html.escape(tb)}</pre>"
                )

                await self.bot.send_message(
                    chat_id=self.admin_id,
                    text=text,
                    parse_mode="HTML",
                )
            except Exception as notify_err:
                logger.error(f"Failed to send error notification to admin: {notify_err}")

            # Пробрасываем исходное исключение дальше (aiogram его залогирует)
            raise
