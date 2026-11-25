"""Standalone Telegram polling runner for local development without webhooks."""

import asyncio
import sys

from app.bot.handlers import get_bot_and_dispatcher
from app.config import get_settings


async def main() -> None:
    settings = get_settings()
    if not settings.TELEGRAM_BOT_TOKEN:
        print("TELEGRAM_BOT_TOKEN is not set in backend/.env. Exiting.")
        sys.exit(1)

    bot, dp = get_bot_and_dispatcher()
    if bot is None:
        print("Failed to initialize Telegram bot.")
        sys.exit(1)

    print("[NoticeSetu] Starting Telegram bot long polling...")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())

