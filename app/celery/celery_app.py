from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "financial-notification-platform",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.celery.tasks",
        "app.celery.scheduled_tasks",
    ],
)

celery_app.conf.update(
    task_serializer=settings.CELERY_TASK_SERIALIZER,
    result_serializer=settings.CELERY_RESULT_SERIALIZER,
    accept_content=[settings.CELERY_ACCEPT_CONTENT],
    timezone=settings.CELERY_TIMEZONE,
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_reject_on_worker_lost=True,
    result_expires=3600,
    task_soft_time_limit=120,
    task_time_limit=300,
    worker_max_tasks_per_child=1000,
    task_routes={
        "app.celery.tasks.send_notification_task": {"queue": "notifications"},
        "app.celery.tasks.retry_notification_task": {"queue": "retries"},
        "app.celery.scheduled_tasks.*": {"queue": "analytics"},
    },
    beat_schedule={
        "aggregate-analytics-daily": {
            "task": "app.celery.scheduled_tasks.aggregate_daily_analytics",
            "schedule": crontab(hour=1, minute=0),
        },
        "retry-failed-notifications": {
            "task": "app.celery.scheduled_tasks.retry_failed_notifications",
            "schedule": crontab(minute="*/5"),
        },
        "cleanup-old-notifications": {
            "task": "app.celery.scheduled_tasks.cleanup_old_notifications",
            "schedule": crontab(hour=3, minute=0),
        },
    },
)
