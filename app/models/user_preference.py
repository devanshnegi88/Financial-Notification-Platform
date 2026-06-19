import uuid
from typing import Optional

from sqlalchemy import Boolean, ForeignKey, Integer, String, Time
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base_model import TimestampMixin, UUIDPrimaryKeyMixin


class UserPreference(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "user_preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    # Channel opt-ins
    sms_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    email_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    whatsapp_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    push_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    in_app_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Event-level opt-outs (comma-separated event types)
    disabled_event_types: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)

    # Quiet hours override
    quiet_hours_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    quiet_hours_start: Mapped[int] = mapped_column(Integer, default=22, nullable=False)
    quiet_hours_end: Mapped[int] = mapped_column(Integer, default=8, nullable=False)

    # Frequency caps override (0 = use global default)
    frequency_cap_hourly: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    frequency_cap_daily: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    frequency_cap_weekly: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Locale
    preferred_locale: Mapped[str] = mapped_column(String(10), default="en", nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="preferences")

    def get_disabled_events(self) -> list[str]:
        if not self.disabled_event_types:
            return []
        return [e.strip() for e in self.disabled_event_types.split(",") if e.strip()]

    def __repr__(self) -> str:
        return f"<UserPreference user_id={self.user_id}>"
