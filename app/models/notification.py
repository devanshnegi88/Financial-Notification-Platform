import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import (
    FinancialEventType,
    NotificationChannel,
    NotificationPriority,
    NotificationStatus,
    SkipReason,
)
from app.db.base import Base
from app.models.base_model import TimestampMixin, UUIDPrimaryKeyMixin


class Notification(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "notifications"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[FinancialEventType] = mapped_column(
        Enum(FinancialEventType, name="financial_event_type_enum"), nullable=False, index=True
    )
    channel: Mapped[NotificationChannel] = mapped_column(
        Enum(NotificationChannel, name="notification_channel_enum"), nullable=False, index=True
    )
    status: Mapped[NotificationStatus] = mapped_column(
        Enum(NotificationStatus, name="notification_status_enum"),
        default=NotificationStatus.PENDING,
        nullable=False,
        index=True,
    )
    priority: Mapped[NotificationPriority] = mapped_column(
        Enum(NotificationPriority, name="notification_priority_enum"),
        default=NotificationPriority.MEDIUM,
        nullable=False,
    )

    # Content
    subject: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    template_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    locale: Mapped[str] = mapped_column(String(10), default="en", nullable=False)

    # Recipient
    recipient: Mapped[str] = mapped_column(String(500), nullable=False)

    # Metadata
    event_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    provider_message_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    provider_response: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Retry tracking
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    next_retry_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Skip info
    skip_reason: Mapped[Optional[SkipReason]] = mapped_column(
        Enum(SkipReason, name="skip_reason_enum"), nullable=True
    )

    # Timing
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Error tracking
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Kafka tracking
    kafka_topic: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    kafka_partition: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    kafka_offset: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Reference ID for idempotency
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True, index=True)

    # Cost tracking (spec Section A8.1: cost_paisa)
    cost_paisa: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # DND classification (spec Section A6.1: TRANSACTIONAL vs PROMOTIONAL)
    classification: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Spec-coded event reference (e.g. "RISK-001") alongside legacy enum event_type
    event_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="notifications")
    delivery_logs: Mapped[list["DeliveryLog"]] = relationship(
        "DeliveryLog", back_populates="notification", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Notification id={self.id} event={self.event_type} channel={self.channel} status={self.status}>"
