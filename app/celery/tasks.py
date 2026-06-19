import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from celery import Task
from celery.utils.log import get_task_logger
from tenacity import retry, stop_after_attempt, wait_exponential

from app.celery.celery_app import celery_app
from app.core.constants import (
    RETRY_DELAY_SCHEDULE,
    DeliveryStatus,
    NotificationStatus,
)

logger = get_task_logger(__name__)


def run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(
    name="app.celery.tasks.send_notification_task",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
    reject_on_worker_lost=True,
)
def send_notification_task(self: Task, notification_id: str) -> dict[str, Any]:
    return run_async(_send_notification_async(self, notification_id))


async def _send_notification_async(task: Task, notification_id: str) -> dict[str, Any]:
    from app.channels.channel_registry import get_channel
    from app.core.constants import NotificationChannel
    from app.db.base import AsyncSessionLocal
    from app.models.delivery_log import DeliveryLog
    from app.repositories.notification_repository import NotificationRepository

    async with AsyncSessionLocal() as session:
        repo = NotificationRepository(session)
        notification = await repo.get(UUID(notification_id))

        if not notification:
            logger.error(f"Notification {notification_id} not found")
            return {"success": False, "error": "Notification not found"}

        if notification.status in (NotificationStatus.DELIVERED, NotificationStatus.CANCELLED):
            return {"success": True, "status": notification.status}

        await repo.update_status(notification.id, NotificationStatus.PROCESSING)

        try:
            channel = get_channel(notification.channel)
            result = await channel.send(
                recipient=notification.recipient,
                subject=notification.subject,
                body=notification.body,
                extra=notification.event_data,
            )

            now = datetime.now(timezone.utc)

            # Record delivery log
            log_data = {
                "notification_id": notification.id,
                "channel": notification.channel,
                "status": DeliveryStatus.DELIVERED if result.success else DeliveryStatus.FAILED,
                "provider": channel.channel_name,
                "provider_message_id": result.provider_message_id,
                "provider_response": result.provider_response,
                "attempt_number": notification.retry_count + 1,
                "sent_at": now if result.success else None,
                "delivered_at": now if result.success else None,
                "error_message": result.error_message,
                "error_code": result.error_code,
                "latency_ms": result.latency_ms,
            }
            await repo.add_delivery_log(log_data)

            if result.success:
                await repo.update_status(
                    notification.id,
                    NotificationStatus.DELIVERED,
                    {
                        "provider_message_id": result.provider_message_id,
                        "provider_response": result.provider_response,
                        "sent_at": now,
                        "delivered_at": now,
                    },
                )
                await session.commit()
                logger.info(f"Notification {notification_id} delivered via {notification.channel}")
                return {"success": True, "message_id": result.provider_message_id}
            else:
                retry_count = notification.retry_count + 1
                if retry_count >= notification.max_retries:
                    await repo.update_status(
                        notification.id,
                        NotificationStatus.DEAD,
                        {
                            "retry_count": retry_count,
                            "error_message": result.error_message,
                            "error_code": result.error_code,
                        },
                    )
                    await session.commit()
                    logger.warning(f"Notification {notification_id} moved to dead letter")
                    return {"success": False, "dead": True}

                delay = RETRY_DELAY_SCHEDULE[min(retry_count, len(RETRY_DELAY_SCHEDULE) - 1)]
                next_retry = datetime.now(timezone.utc) + timedelta(seconds=delay)
                await repo.update_status(
                    notification.id,
                    NotificationStatus.RETRYING,
                    {
                        "retry_count": retry_count,
                        "next_retry_at": next_retry,
                        "error_message": result.error_message,
                        "error_code": result.error_code,
                    },
                )
                await session.commit()

                retry_notification_task.apply_async(
                    args=[notification_id],
                    countdown=delay,
                    queue="retries",
                )
                return {"success": False, "retrying": True, "retry_in": delay}

        except Exception as e:
            await session.rollback()
            logger.error(f"Notification {notification_id} send error: {e}")
            async with AsyncSessionLocal() as s2:
                repo2 = NotificationRepository(s2)
                notif = await repo2.get(UUID(notification_id))
                if notif:
                    retry_count = notif.retry_count + 1
                    if retry_count >= notif.max_retries:
                        await repo2.update_status(
                            notif.id, NotificationStatus.DEAD, {"error_message": str(e)}
                        )
                    else:
                        delay = RETRY_DELAY_SCHEDULE[min(retry_count, len(RETRY_DELAY_SCHEDULE) - 1)]
                        next_retry = datetime.now(timezone.utc) + timedelta(seconds=delay)
                        await repo2.update_status(
                            notif.id,
                            NotificationStatus.RETRYING,
                            {"retry_count": retry_count, "next_retry_at": next_retry, "error_message": str(e)},
                        )
                    await s2.commit()
            return {"success": False, "error": str(e)}


@celery_app.task(
    name="app.celery.tasks.retry_notification_task",
    bind=True,
    max_retries=1,
    acks_late=True,
)
def retry_notification_task(self: Task, notification_id: str) -> dict[str, Any]:
    return run_async(_retry_async(notification_id))


async def _retry_async(notification_id: str) -> dict[str, Any]:
    from app.db.base import AsyncSessionLocal
    from app.repositories.notification_repository import NotificationRepository

    async with AsyncSessionLocal() as session:
        repo = NotificationRepository(session)
        notification = await repo.get(UUID(notification_id))
        if not notification:
            return {"success": False, "error": "Not found"}

        await repo.update_status(notification.id, NotificationStatus.PENDING)
        await session.commit()

    send_notification_task.apply_async(args=[notification_id], queue="notifications")
    return {"success": True, "requeued": True}
