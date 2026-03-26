from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "task_manager",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["tasks.reminder_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    # Beat schedule: run reminder check every 15 minutes
    beat_schedule={
        "send-deadline-reminders": {
            "task": "tasks.reminder_tasks.send_deadline_reminders",
            "schedule": crontab(minute="*/15"),
        },
    },
)
