"""
Event Ingestion API per ZeTheta spec Appendix A.

POST /api/v1/events
Accepts a new financial event using the spec's coded taxonomy (TXNX-001, RISK-001, etc.)
Returns notification_id, channels_targeted, estimated_delivery_ms as per spec.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.event_taxonomy import (
    EVENT_REGISTRY,
    get_mandatory_channels,
    get_priority_for_event,
    is_dnd_exempt,
    is_quiet_hours_exempt,
)
from app.core.logging import get_logger
from app.db.base import get_db
from app.kafka.producer import NotificationEventProducer, get_producer
from app.middleware.auth_middleware import CurrentUser, get_current_user, require_manager
from app.rabbitmq.publisher import NotificationPublisher

logger = get_logger(__name__)

router = APIRouter(prefix="/events", tags=["Event Ingestion"])

# Per-channel estimated delivery times in milliseconds (from spec A3.1)
CHANNEL_ESTIMATED_DELIVERY_MS = {
    "sms": 7000,       # 3-10s avg
    "push": 500,       # <1s
    "email": 30000,    # 1-60s
    "whatsapp": 3500,  # 2-5s
    "in_app": 100,     # real-time
    "call": 30000,     # 15-45s
}


class EventPayload(BaseModel):
    """Spec Appendix A: exact event ingestion request body."""
    event_type: str = Field(description="Event code e.g. RISK-001, TXNX-001")
    event_id: str = Field(description="External event reference ID")
    source_system: str = Field(description="Originating system e.g. margin_engine")
    timestamp: datetime
    priority: int = Field(default=3, ge=1, le=5, description="1=CRITICAL, 2=HIGH, 3=MEDIUM, 5=LOW")
    user_id: UUID
    payload: Dict[str, Any] = Field(default_factory=dict)
    idempotency_key: Optional[str] = None
    channels: Optional[List[str]] = None  # None = auto-select per taxonomy

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, v: str) -> str:
        # Accept both spec codes (RISK-001) and legacy enum values (transaction.success)
        return v

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: int) -> int:
        if v not in (1, 2, 3, 5):
            raise ValueError("Priority must be 1 (CRITICAL), 2 (HIGH), 3 (MEDIUM), or 5 (LOW)")
        return v


class EventIngestionResponse(BaseModel):
    """Spec Appendix A: exact event ingestion response."""
    notification_id: str
    event_id: str
    status: str = "CREATED"
    channels_targeted: List[str]
    estimated_delivery_ms: int
    created_at: str


class ValidationErrorDetail(BaseModel):
    field: str
    error: str


class ValidationErrorResponse(BaseModel):
    error: str = "VALIDATION_FAILED"
    message: str
    details: List[ValidationErrorDetail]
    request_id: str


def _resolve_channels(event_type: str, requested_channels: Optional[List[str]]) -> List[str]:
    """Determine which channels to use based on taxonomy and request."""
    event_def = EVENT_REGISTRY.get(event_type)

    if requested_channels:
        # Always include mandatory channels even if not in request
        mandatory = [c.value for c in get_mandatory_channels(event_type)]
        merged = list(set(requested_channels + mandatory))
        return merged

    if event_def:
        return [c.value for c in event_def.channels]

    # Fallback for unknown event types
    return ["push", "in_app"]


def _estimate_delivery_ms(channels: List[str], priority: int) -> int:
    """Estimate fastest delivery time across selected channels."""
    if not channels:
        return 5000
    min_latency = min(CHANNEL_ESTIMATED_DELIVERY_MS.get(ch, 10000) for ch in channels)
    # Critical events get priority queue bonus
    if priority == 1:
        min_latency = int(min_latency * 0.5)
    return min_latency


@router.post(
    "",
    response_model=EventIngestionResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        422: {"model": ValidationErrorResponse, "description": "Validation failed"},
    },
)
async def ingest_event(
    payload: EventPayload,
    current_user: CurrentUser = Depends(require_manager),
    db: AsyncSession = Depends(get_db),
):
    """
    Primary entry point for all financial event producers.
    Accepts coded events (TXNX-001, RISK-001, etc.) and routes to Kafka → RabbitMQ.
    """
    notification_id = str(uuid4())
    channels = _resolve_channels(payload.event_type, payload.channels)
    estimated_ms = _estimate_delivery_ms(channels, payload.priority)

    # Determine actual priority from taxonomy if not explicitly overridden
    taxonomy_priority = get_priority_for_event(payload.event_type)
    effective_priority = payload.priority
    # CRITICAL events from taxonomy always use priority 1 regardless of request
    if taxonomy_priority and taxonomy_priority.value == 1:
        effective_priority = 1

    event_data = {
        "notification_id": notification_id,
        "user_id": str(payload.user_id),
        "event_type": payload.event_type,
        "event_id": payload.event_id,
        "source_system": payload.source_system,
        "timestamp": payload.timestamp.isoformat(),
        "priority": effective_priority,
        "channels": channels,
        "event_data": payload.payload,
        "idempotency_key": payload.idempotency_key,
        "bypass_dnd": is_dnd_exempt(payload.event_type),
        "bypass_quiet_hours": is_quiet_hours_exempt(payload.event_type),
    }

    # Publish to Kafka for event streaming and fan-out
    try:
        producer = await get_producer()
        event_producer = NotificationEventProducer(producer)
        await event_producer.publish_notification_event(
            payload=event_data,
            partition_key=str(payload.user_id),
        )
    except Exception as e:
        logger.error("event_kafka_publish_failed", error=str(e), event_id=payload.event_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Event queue temporarily unavailable. Please retry.",
        )

    # Also publish to RabbitMQ priority queue for immediate delivery routing
    try:
        publisher = NotificationPublisher()
        for channel in channels:
            await publisher.publish(
                notification_id=notification_id,
                channel=channel,
                priority=effective_priority,
                event_data=payload.payload,
            )
    except Exception as e:
        logger.warning("rabbitmq_publish_failed_non_critical", error=str(e))
        # Non-fatal: Kafka consumer will still process the event

    logger.info(
        "event_ingested",
        notification_id=notification_id,
        event_type=payload.event_type,
        event_id=payload.event_id,
        user_id=str(payload.user_id),
        priority=effective_priority,
        channels=channels,
    )

    return EventIngestionResponse(
        notification_id=notification_id,
        event_id=payload.event_id,
        status="CREATED",
        channels_targeted=channels,
        estimated_delivery_ms=estimated_ms,
        created_at=datetime.now(timezone.utc).isoformat(),
    )


@router.post(
    "/bulk",
    response_model=dict,
    status_code=status.HTTP_202_ACCEPTED,
)
async def bulk_ingest_events(
    events: List[EventPayload],
    current_user: CurrentUser = Depends(require_manager),
    db: AsyncSession = Depends(get_db),
):
    """Bulk event ingestion for broadcasting same event to multiple users."""
    if len(events) > 10000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 10,000 events per bulk request",
        )

    producer = await get_producer()
    event_producer = NotificationEventProducer(producer)

    results = []
    for event in events:
        notification_id = str(uuid4())
        channels = _resolve_channels(event.event_type, event.channels)

        await event_producer.publish_notification_event(
            payload={
                "notification_id": notification_id,
                "user_id": str(event.user_id),
                "event_type": event.event_type,
                "event_id": event.event_id,
                "priority": event.priority,
                "channels": channels,
                "event_data": event.payload,
                "idempotency_key": event.idempotency_key,
            },
            partition_key=str(event.user_id),
        )
        results.append({"notification_id": notification_id, "event_id": event.event_id})

    return {
        "accepted": len(results),
        "notifications": results,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
