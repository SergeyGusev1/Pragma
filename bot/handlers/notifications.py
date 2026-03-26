"""
Telegram bot handlers.

/start  - welcome message
/link <token>  - link Telegram account to the Task Manager app
"""

import logging

from aiogram import Router, types
from aiogram.filters import Command, CommandObject
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.models.user import User

router = Router()
logger = logging.getLogger(__name__)


def _get_sync_session() -> Session:
    engine = create_engine(settings.database_url_sync)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


@router.message(Command("start"))
async def cmd_start(message: types.Message) -> None:
    await message.answer(
        "👋 Welcome to <b>Task Manager Bot</b>!\n\n"
        "To receive task deadline reminders, link your account:\n"
        "1. Go to the app and request a link token via <code>POST /api/v1/users/me/telegram-link</code>\n"
        "2. Send me the token: <code>/link YOUR_TOKEN</code>"
    )


@router.message(Command("link"))
async def cmd_link(message: types.Message, command: CommandObject) -> None:
    token = command.args
    if not token:
        await message.answer("Usage: /link <token>\n\nGet your token from the app.")
        return

    session = _get_sync_session()
    try:
        user = session.execute(
            select(User).where(User.telegram_link_token == token.strip())
        ).scalar_one_or_none()

        if not user:
            await message.answer("❌ Invalid or expired token. Please generate a new one from the app.")
            return

        user.telegram_chat_id = message.chat.id
        user.telegram_link_token = None  # Consume the token (one-time use)
        session.commit()

        await message.answer(
            f"✅ Successfully linked!\n\n"
            f"Your Telegram account is now connected to <b>{user.username}</b>.\n"
            f"You will receive reminders 24 hours before task deadlines."
        )
        logger.info(f"User {user.id} linked Telegram chat {message.chat.id}")

    except Exception as e:
        session.rollback()
        logger.exception(f"Error linking Telegram account: {e}")
        await message.answer("❌ An error occurred. Please try again later.")
    finally:
        session.close()
