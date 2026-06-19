from datetime import date
from typing import Optional

from sqlalchemy import BigInteger, Date, Enum, Float, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import FinancialEventType, NotificationChannel
from app.db.base import Base
from app.models.base_model import TimestampMixin, UUIDPrimaryKeyMixin


class NotificationAnalytics(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "notification_analytics"
    __table_args__ = (
        UniqueConstraint("date", "event_type", "channel", name="uq_analytics_date_event_channel"),
    )

    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    event_type: Mapped[FinancialEventType] = mapped_column(
        Enum(FinancialEventType, name="analytics_event_type_enum"), nullable=False, index=True
    )
    channel: Mapped[NotificationChannel] = mapped_column(
        Enum(NotificationChannel, name="analytics_channel_enum"), nullable=False, index=True
    )

    # Counters
    total_sent: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    total_delivered: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    total_failed: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    total_skipped: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    total_retried: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    total_dead: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    total_opened: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    total_clicked: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)

    # Skip breakdown
    skip_dnd: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    skip_quiet_hours: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    skip_frequency_cap: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    skip_user_opt_out: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)

    # Performance
    avg_latency_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    p95_latency_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    delivery_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    open_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    click_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    def __repr__(self) -> str:
        return f"<NotificationAnalytics date={self.date} event={self.event_type} channel={self.channel}>"
