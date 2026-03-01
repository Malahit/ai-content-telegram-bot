"""Unified entry point for AI Content Telegram Bot.

Run this file in production (Railway Worker) and locally:
    python main.py

This keeps a single canonical entrypoint while the full bot logic lives in bot.py.
"""

import asyncio

from bot import main as bot_main


if __name__ == "__main__":
    asyncio.run(bot_main())
