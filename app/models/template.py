from typing import Optional

from sqlalchemy import Boolean, Enum, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import FinancialEventType, NotificationChannel
from app.db.base import Base
from app.models.base_model import TimestampMixin, UUIDPrimaryKeyMixin


class NotificationTemplate(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "notification_templates"
    __table_args__ = (
        UniqueConstraint("event_type", "channel", "locale", name="uq_template_event_channel_locale"),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    event_type: Mapped[FinancialEventType] = mapped_column(
        Enum(FinancialEventType, name="tmpl_event_type_enum"), nullable=False, index=True
    )
    channel: Mapped[NotificationChannel] = mapped_column(
        Enum(NotificationChannel, name="tmpl_channel_enum"), nullable=False, index=True
    )
    locale: Mapped[str] = mapped_column(String(10), default="en", nullable=False)
    subject: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    html_body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    variables: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    version: Mapped[int] = mapped_column(default=1, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<NotificationTemplate event={self.event_type} channel={self.channel} locale={self.locale}>"
