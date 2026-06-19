from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import DeliveryStatus, NotificationStatus
from app.core.logging import get_logger
from app.models.delivery_log import DeliveryLog
from app.models.notification import Notification
from app.repositories.notification_repository import NotificationRepository

logger = get_logger(__name__)


class DeliveryTrackingService:
    """
    Handles webhook callbacks and provider delivery receipts to update
    notification delivery status in real time.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = NotificationRepository(session)

    async def handle_delivery_receipt(
        self,
        provider: str,
        provider_message_id: str,
        status: DeliveryStatus,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Optional[Notification]:
        # Find notification by provider_message_id
        result = await self.session.execute(
            select(Notification).where(
                Notification.provider_message_id == provider_message_id
            )
        )
        notification = result.scalar_one_or_none()
        if not notification:
            logger.warning(
                "delivery_receipt_notification_not_found",
                provider=provider,
                provider_message_id=provider_message_id,
            )
            return None

        now = datetime.now(timezone.utc)
        updates: Dict[str, Any] = {}

        if status == DeliveryStatus.DELIVERED:
            updates["status"] = NotificationStatus.DELIVERED
            updates["delivered_at"] = now
        elif status == DeliveryStatus.FAILED or status == DeliveryStatus.BOUNCED:
            updates["status"] = NotificationStatus.FAILED
            updates["error_message"] = (extra or {}).get("error_message", "Provider reported failure")
        elif status == DeliveryStatus.OPENED:
            updates["read_at"] = now

        if updates:
            notification = await self.repo.update_status(
                notification.id,
                updates.pop("status", notification.status),
                updates,
            )

        # Log delivery event
        log = DeliveryLog(
            notification_id=notification.id,
            channel=notification.channel,
            status=status,
            provider=provider,
            provider_message_id=provider_message_id,
            provider_response=extra,
            attempt_number=notification.retry_count + 1,
            delivered_at=now if status == DeliveryStatus.DELIVERED else None,
        )
        self.session.add(log)
        await self.session.flush()

        logger.info(
            "delivery_receipt_processed",
            notification_id=str(notification.id),
            provider=provider,
            status=status,
        )
        return notification

    async def get_delivery_timeline(self, notification_id: UUID) -> list[dict]:
        result = await self.session.execute(
            select(DeliveryLog)
            .where(DeliveryLog.notification_id == notification_id)
            .order_by(DeliveryLog.created_at)
        )
        logs = result.scalars().all()
        return [
            {
                "attempt": log.attempt_number,
                "status": log.status,
                "provider": log.provider,
                "provider_message_id": log.provider_message_id,
                "sent_at": log.sent_at.isoformat() if log.sent_at else None,
                "delivered_at": log.delivered_at.isoformat() if log.delivered_at else None,
                "latency_ms": log.latency_ms,
                "error_message": log.error_message,
                "created_at": log.created_at.isoformat(),
            }
            for log in logs
        ]
