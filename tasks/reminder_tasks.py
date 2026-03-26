"""
Celery task that scans for tasks with deadlines in the next 24 hours
and sends Telegram notifications to assigned users.

Note: Celery tasks run in a synchronous context. We use asyncio.run()
to bridge into the async SQLAlchemy world.
"""

import logging
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.models.task import Task, TaskStatus
from tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


def _get_sync_session():
    """Create a synchronous SQLAlchemy session for use inside Celery tasks."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(settings.database_url_sync)
    session_factory = sessionmaker(bind=engine)
    return session_factory()


def _send_telegram_message(chat_id: int, text: str) -> bool:
    """Send a message via the Telegram Bot API. Returns True on success."""
    if not settings.telegram_bot_token:
        logger.warning("TELEGRAM_BOT_TOKEN is not set, skipping notification")
        return False

    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    try:
        response = httpx.post(
            url,
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=10,
        )
        response.raise_for_status()
        return True
    except httpx.HTTPError as e:
        logger.error(f"Failed to send Telegram message to {chat_id}: {e}")
        return False


@celery_app.task(
    name="tasks.reminder_tasks.send_deadline_reminders", bind=True, max_retries=3
)
def send_deadline_reminders(self):
    """
    Scan for tasks due within the next 24 hours and notify assignees via Telegram.
    Sets reminder_sent=True to prevent duplicate notifications.
    """
    now = datetime.now(UTC).replace(tzinfo=None)
    deadline_window_end = now + timedelta(hours=24)

    session: Session = _get_sync_session()
    sent_count = 0
    error_count = 0

    try:
        # Find tasks due within the next 24 hours where reminder hasn't been sent
        stmt = (
            select(Task)
            .where(
                Task.deadline >= now,
                Task.deadline <= deadline_window_end,
                Task.reminder_sent.is_(False),
                Task.status != TaskStatus.done,
            )
            .options(
                selectinload(Task.assignee),
                selectinload(Task.project),
            )
        )
        tasks = session.execute(stmt).scalars().all()

        logger.info(f"Found {len(tasks)} tasks due for reminder")

        for task in tasks:
            if task.assignee is None or task.assignee.telegram_chat_id is None:
                # No assignee or no Telegram — mark as sent to avoid re-checking
                task.reminder_sent = True
                continue

            deadline_str = task.deadline.strftime("%Y-%m-%d %H:%M UTC")
            message = (
                f"⏰ <b>Task Deadline Reminder</b>\n\n"
                f"📌 <b>{task.title}</b>\n"
                f"📁 Project: {task.project.name}\n"
                f"🔴 Priority: {task.priority.value.upper()}\n"
                f"⏳ Deadline: {deadline_str}\n\n"
                f"Don't forget to complete it on time!"
            )

            success = _send_telegram_message(task.assignee.telegram_chat_id, message)
            if success:
                task.reminder_sent = True
                sent_count += 1
            else:
                error_count += 1

        session.commit()
        logger.info(f"Reminders sent: {sent_count}, errors: {error_count}")

    except Exception as exc:
        session.rollback()
        logger.exception(f"Reminder task failed: {exc}")
        raise self.retry(exc=exc, countdown=60) from exc
    finally:
        session.close()
