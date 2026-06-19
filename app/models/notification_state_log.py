import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class NotificationStateLog(Base):
    """
    Immutable audit log of every notification state transition.
    Required for SEBI/TRAI compliance audit (Section A7.1).
    Records: CREATED → ENRICHED → ROUTED → QUEUED → SENT → DELIVERED → READ
    Plus: CAPPED, QUIET, DND branch states.
    """

    __tablename__ = "notification_state_log"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    notification_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("notifications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    from_status: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    to_status: Mapped[str] = mapped_column(String(30), nullable=False)
    actor: Mapped[str] = mapped_column(String(80), nullable=False)
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    def __repr__(self) -> str:
        return (
            f"<NotificationStateLog id={self.id} "
            f"notification_id={self.notification_id} "
            f"{self.from_status}→{self.to_status} actor={self.actor}>"
        )
