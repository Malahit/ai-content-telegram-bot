"""
Referral system handlers.

Commands:
- /referral — show referral link and stats
- /top_referrals — leaderboard (admin only)
"""

from urllib.parse import quote

from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from services.referral_service import (
    ensure_referral_code,
    get_referral_stats,
    get_top_referrers,
    REFERRAL_BONUS_POSTS,
)
from services.user_service import is_user_admin
from logger_config import logger

BOT_USERNAME = "ai_content_helper_bot"
FREE_DAILY_LIMIT = 3

router = Router(name="referral")


@router.message(Command("referral"))
async def cmd_referral(message: types.Message):
    """Show user's referral link and statistics."""
    telegram_id = message.from_user.id

    code = await ensure_referral_code(telegram_id)
    if not code:
        await message.answer("❌ Не удалось получить реферальный код. Попробуйте /start.")
        return

    stats = await get_referral_stats(telegram_id)
    count = stats["referrals_count"] if stats else 0
    bonus = stats["bonus_posts"] if stats else 0

    referral_link = f"https://t.me/{BOT_USERNAME}?start=ref_{code}"
    share_text = "AI-бот генерирует посты для TG-каналов за 15 секунд. Попробуй — 3 поста в день бесплатно!"
    share_url = f"https://t.me/share/url?url={quote(referral_link)}&text={quote(share_text)}"

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📤 Поделиться ссылкой", url=share_url)]
        ]
    )

    await message.answer(
        f"🔗 <b>Ваша реферальная ссылка:</b>\n\n"
        f"<code>{referral_link}</code>\n\n"
        f"📊 <b>Статистика:</b>\n"
        f"├ Приглашено друзей: {count}\n"
        f"├ Бонусных постов/день: +{bonus}\n"
        f"└ Ваш дневной лимит: {FREE_DAILY_LIMIT + bonus} постов\n\n"
        f"За каждого друга вы получаете +{REFERRAL_BONUS_POSTS} поста к дневному лимиту навсегда!",
        reply_markup=keyboard,
    )


@router.message(Command("top_referrals"))
async def cmd_top_referrals(message: types.Message):
    """Show referral leaderboard (admin only)."""
    telegram_id = message.from_user.id

    if not await is_user_admin(telegram_id):
        await message.answer("🚫 <b>Эта команда доступна только администраторам.</b>")
        return

    top = await get_top_referrers(limit=10)
    if not top:
        await message.answer("📊 Пока нет данных по рефералам.")
        return

    lines = ["🏆 <b>Топ рефералов:</b>\n"]
    for i, entry in enumerate(top, 1):
        username = f"@{entry['username']}" if entry["username"] else f"ID:{entry['telegram_id']}"
        lines.append(f"{i}. {username} — {entry['referrals_count']} приглашений")

    await message.answer("\n".join(lines))
