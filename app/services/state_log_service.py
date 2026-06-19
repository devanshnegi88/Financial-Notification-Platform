from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.notification_state_log import NotificationStateLog

logger = get_logger(__name__)


class StateLogService:
    """
    Records every notification state transition to notification_state_log.
    This provides the complete audit trail required for SEBI/TRAI compliance.
    Supports replay of notification history for any notification ID.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def record(
        self,
        notification_id: UUID,
        from_status: Optional[str],
        to_status: str,
        actor: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> NotificationStateLog:
        log = NotificationStateLog(
            notification_id=notification_id,
            from_status=from_status,
            to_status=to_status,
            actor=actor,
            metadata_=metadata,
        )
        self.session.add(log)
        await self.session.flush()

        logger.info(
            "notification_state_transition",
            notification_id=str(notification_id),
            from_status=from_status,
            to_status=to_status,
            actor=actor,
        )
        return log

    async def get_history(self, notification_id: UUID) -> list[dict]:
        result = await self.session.execute(
            select(NotificationStateLog)
            .where(NotificationStateLog.notification_id == notification_id)
            .order_by(NotificationStateLog.created_at)
        )
        logs = result.scalars().all()
        return [
            {
                "status": log.to_status,
                "from_status": log.from_status,
                "timestamp": log.created_at.isoformat(),
                "actor": log.actor,
                "metadata": log.metadata_,
            }
            for log in logs
        ]

    async def record_created(self, notification_id: UUID) -> None:
        await self.record(notification_id, None, "CREATED", "event_ingestion")

    async def record_enriched(self, notification_id: UUID, channels: list[str]) -> None:
        await self.record(
            notification_id, "CREATED", "ENRICHED", "enrichment_worker",
            {"channels_resolved": channels}
        )

    async def record_routed(self, notification_id: UUID, channel: str, routing_key: str) -> None:
        await self.record(
            notification_id, "ENRICHED", "ROUTED", "routing_engine",
            {"channel": channel, "routing_key": routing_key}
        )

    async def record_queued(self, notification_id: UUID, queue: str) -> None:
        await self.record(
            notification_id, "ROUTED", "QUEUED", "rabbitmq_publisher",
            {"queue": queue}
        )

    async def record_sent(
        self, notification_id: UUID, provider: str, external_id: Optional[str] = None
    ) -> None:
        await self.record(
            notification_id, "QUEUED", "SENT", f"{provider}_delivery_worker",
            {"provider": provider, "external_id": external_id}
        )

    async def record_delivered(
        self, notification_id: UUID, provider: str, latency_ms: Optional[int] = None
    ) -> None:
        await self.record(
            notification_id, "SENT", "DELIVERED", "dlr_webhook_handler",
            {"provider": provider, "latency_ms": latency_ms}
        )

    async def record_failed(
        self, notification_id: UUID, reason: str, error_code: Optional[str] = None
    ) -> None:
        await self.record(
            notification_id, None, "FAILED", "delivery_worker",
            {"reason": reason, "error_code": error_code}
        )

    async def record_retrying(
        self, notification_id: UUID, attempt: int, next_retry_seconds: int
    ) -> None:
        await self.record(
            notification_id, "FAILED", "RETRYING", "retry_worker",
            {"attempt": attempt, "next_retry_in_seconds": next_retry_seconds}
        )

    async def record_dead(self, notification_id: UUID, total_attempts: int) -> None:
        await self.record(
            notification_id, "RETRYING", "DLQ", "retry_worker",
            {"total_attempts": total_attempts, "reason": "max_retries_exhausted"}
        )

    async def record_capped(self, notification_id: UUID, cap_type: str) -> None:
        await self.record(
            notification_id, "ROUTED", "CAPPED", "frequency_cap_service",
            {"cap_type": cap_type}
        )

    async def record_quiet_hours(
        self, notification_id: UUID, scheduled_delivery_time: str
    ) -> None:
        await self.record(
            notification_id, "ROUTED", "QUIET", "quiet_hours_enforcer",
            {"scheduled_delivery": scheduled_delivery_time,
             "audit": "quiet_hours_bypass_not_applicable"}
        )

    async def record_dnd_blocked(
        self, notification_id: UUID, dnd_check_timestamp: str, classification: str
    ) -> None:
        await self.record(
            notification_id, "ROUTED", "DND_BLOCKED", "dnd_service",
            {
                "dnd_check_timestamp": dnd_check_timestamp,
                "classification": classification,
                "audit": "trai_dnd_compliance",
            }
        )

    async def record_read(self, notification_id: UUID) -> None:
        await self.record(notification_id, "DELIVERED", "READ", "user_action")
