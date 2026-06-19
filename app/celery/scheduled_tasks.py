import asyncio
from datetime import date, datetime, timedelta, timezone

from celery.utils.log import get_task_logger

from app.celery.celery_app import celery_app

logger = get_task_logger(__name__)


def run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="app.celery.scheduled_tasks.aggregate_daily_analytics")
def aggregate_daily_analytics():
    return run_async(_aggregate_analytics())


async def _aggregate_analytics():
    from app.db.base import AsyncSessionLocal
    from app.services.analytics_service import AnalyticsService

    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).date()
    async with AsyncSessionLocal() as session:
        service = AnalyticsService(session)
        await service.upsert_daily_aggregates(yesterday)
        await session.commit()
    logger.info(f"Analytics aggregated for {yesterday}")
    return {"date": str(yesterday)}


@celery_app.task(name="app.celery.scheduled_tasks.retry_failed_notifications")
def retry_failed_notifications():
    return run_async(_retry_failed())


async def _retry_failed():
    from app.celery.tasks import send_notification_task
    from app.db.base import AsyncSessionLocal
    from app.repositories.notification_repository import NotificationRepository

    async with AsyncSessionLocal() as session:
        repo = NotificationRepository(session)
        notifications = await repo.get_pending_retries(limit=100)

        count = 0
        for notification in notifications:
            send_notification_task.apply_async(
                args=[str(notification.id)],
                queue="notifications",
            )
            count += 1

    logger.info(f"Requeued {count} notifications for retry")
    return {"requeued": count}


@celery_app.task(name="app.celery.scheduled_tasks.cleanup_old_notifications")
def cleanup_old_notifications():
    return run_async(_cleanup())


async def _cleanup():
    from sqlalchemy import and_, delete
    from app.core.constants import NotificationStatus
    from app.db.base import AsyncSessionLocal
    from app.models.notification import Notification

    cutoff = datetime.now(timezone.utc) - timedelta(days=90)
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            delete(Notification).where(
                and_(
                    Notification.created_at < cutoff,
                    Notification.status.in_([
                        NotificationStatus.DELIVERED,
                        NotificationStatus.SKIPPED,
                        NotificationStatus.DEAD,
                        NotificationStatus.CANCELLED,
                    ]),
                )
            )
        )
        await session.commit()
        deleted = result.rowcount

    logger.info(f"Cleaned up {deleted} old notifications")
    return {"deleted": deleted}
