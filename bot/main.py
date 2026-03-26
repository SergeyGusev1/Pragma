"""
Telegram Bot entry point.
Runs as a standalone process alongside the FastAPI app.
"""

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.core.config import settings
from bot.handlers import notifications

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main() -> None:
    if not settings.telegram_bot_token:
        logger.error("TELEGRAM_BOT_TOKEN is not set. Bot cannot start.")
        return

    bot = Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.include_router(notifications.router)

    @dp.startup()
    async def on_startup() -> None:
        if settings.telegram_admin_chat_id:
            await bot.send_message(
                settings.telegram_admin_chat_id,
                "✅ <b>Бот запущен</b> и готов к работе.",
            )

    logger.info("Starting Telegram bot...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
