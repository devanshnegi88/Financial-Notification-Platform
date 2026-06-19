from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.constants import (
    FinancialEventType,
    NotificationChannel,
    NotificationPriority,
    NotificationStatus,
    SkipReason,
)


class NotificationEventPayload(BaseModel):
    """Payload published to Kafka when a financial event occurs."""
    user_id: UUID
    event_type: FinancialEventType
    priority: NotificationPriority = NotificationPriority.MEDIUM
    channels: Optional[List[NotificationChannel]] = None  # None = auto-select
    event_data: Dict[str, Any] = Field(default_factory=dict)
    locale: Optional[str] = None  # None = use user's preference
    idempotency_key: Optional[str] = None
    scheduled_at: Optional[datetime] = None


class NotificationCreate(BaseModel):
    user_id: UUID
    event_type: FinancialEventType
    channel: NotificationChannel
    priority: NotificationPriority = NotificationPriority.MEDIUM
    recipient: str
    subject: Optional[str] = None
    body: str
    template_id: Optional[str] = None
    locale: str = "en"
    event_data: Optional[Dict[str, Any]] = None
    idempotency_key: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    max_retries: int = 3


class NotificationResponse(BaseModel):
    id: UUID
    user_id: UUID
    event_type: FinancialEventType
    channel: NotificationChannel
    status: NotificationStatus
    priority: NotificationPriority
    subject: Optional[str]
    body: str
    locale: str
    recipient: str
    retry_count: int
    max_retries: int
    skip_reason: Optional[SkipReason]
    sent_at: Optional[datetime]
    delivered_at: Optional[datetime]
    read_at: Optional[datetime]
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class NotificationListResponse(BaseModel):
    id: UUID
    event_type: FinancialEventType
    channel: NotificationChannel
    status: NotificationStatus
    priority: NotificationPriority
    subject: Optional[str]
    sent_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationFilter(BaseModel):
    user_id: Optional[UUID] = None
    event_type: Optional[FinancialEventType] = None
    channel: Optional[NotificationChannel] = None
    status: Optional[NotificationStatus] = None
    priority: Optional[NotificationPriority] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None


class MarkReadRequest(BaseModel):
    notification_ids: List[UUID]


class BulkEventRequest(BaseModel):
    """Trigger same event for multiple users."""
    user_ids: List[UUID]
    event_type: FinancialEventType
    priority: NotificationPriority = NotificationPriority.MEDIUM
    channels: Optional[List[NotificationChannel]] = None
    event_data: Dict[str, Any] = Field(default_factory=dict)
