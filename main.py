"""
Compatibility entry point – delegates to bot.py.

The canonical runtime entry point for this application is ``bot.py``.
All bot logic, handlers, and startup code live there.

This file exists solely for backward compatibility (e.g. scripts or deploy
configs that still reference ``main.py``).  It simply imports and runs the
``main()`` coroutine from ``bot.py``.

To run the bot use:
    python bot.py

Railway start command (also reflected in Procfile):
    python bot.py
"""

import asyncio

from bot import main

if __name__ == "__main__":
    asyncio.run(main())
