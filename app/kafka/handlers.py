import asyncio
from datetime import datetime, timezone
from typing import Any, Dict
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import NotificationStatus, RETRY_DELAY_SCHEDULE
from app.core.logging import get_logger
from app.kafka.producer import NotificationEventProducer, get_producer
from app.repositories.notification_repository import NotificationRepository
from app.services.notification_dispatcher import NotificationDispatcher
from app.services.notification_factory import NotificationFactory

logger = get_logger(__name__)


class NotificationEventHandler:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.factory = NotificationFactory(session)
        self.dispatcher = NotificationDispatcher(session)
        self.repo = NotificationRepository(session)

    async def handle(self, payload: Dict[str, Any]) -> None:
        try:
            user_id = UUID(payload["user_id"])
            event_type = payload["event_type"]
            priority = payload.get("priority", "medium")
            channels = payload.get("channels")
            event_data = payload.get("event_data", {})
            locale = payload.get("locale")
            idempotency_key = payload.get("idempotency_key")

            # Check idempotency
            if idempotency_key:
                existing = await self.repo.get_by_idempotency_key(idempotency_key)
                if existing:
                    logger.info("idempotent_skip", idempotency_key=idempotency_key)
                    return

            # Build notifications for each eligible channel
            notifications = await self.factory.build_notifications(
                user_id=user_id,
                event_type=event_type,
                priority=priority,
                channels=channels,
                event_data=event_data,
                locale=locale,
                idempotency_key=idempotency_key,
            )

            # Dispatch each notification
            for notification in notifications:
                await self.dispatcher.dispatch(notification)

            await self.session.commit()

        except Exception as e:
            await self.session.rollback()
            logger.error("notification_event_handler_failed", error=str(e), payload=payload)

            # Send to DLQ
            try:
                producer = await get_producer()
                event_producer = NotificationEventProducer(producer)
                await event_producer.publish_to_dlq(payload, str(e))
            except Exception as dlq_error:
                logger.error("dlq_publish_failed", error=str(dlq_error))


class RetryEventHandler:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.dispatcher = NotificationDispatcher(session)
        self.repo = NotificationRepository(session)

    async def handle(self, payload: Dict[str, Any]) -> None:
        notification_id_str = payload.get("notification_id")
        if not notification_id_str:
            logger.error("retry_missing_notification_id", payload=payload)
            return

        try:
            notification_id = UUID(notification_id_str)
            notification = await self.repo.get(notification_id)

            if not notification:
                logger.warning("retry_notification_not_found", notification_id=notification_id_str)
                return

            if notification.retry_count >= notification.max_retries:
                await self.repo.update_status(
                    notification_id,
                    NotificationStatus.DEAD,
                    {"error_message": "Max retries exhausted"},
                )
                await self.session.commit()
                logger.warning("notification_moved_to_dead", notification_id=notification_id_str)
                return

            await self.dispatcher.dispatch(notification)
            await self.session.commit()

        except Exception as e:
            await self.session.rollback()
            logger.error("retry_handler_failed", error=str(e), notification_id=notification_id_str)
