import time
from typing import Any, Dict, Optional

from app.channels.base import BaseChannel, ChannelResult
from app.core.logging import get_logger

logger = get_logger(__name__)


class InAppChannel(BaseChannel):
    @property
    def channel_name(self) -> str:
        return "in_app"

    async def send(
        self,
        recipient: str,
        subject: Optional[str],
        body: str,
        html_body: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> ChannelResult:
        start = time.monotonic()
        # In-app notifications are stored directly in the DB.
        # The record already exists as a Notification row.
        # This channel just "delivers" it by marking it delivered.
        latency_ms = int((time.monotonic() - start) * 1000)
        logger.info("in_app_notification_stored", user_id=recipient, latency_ms=latency_ms)
        return ChannelResult(
            success=True,
            provider_message_id=f"in_app:{recipient}",
            provider_response={"stored": True},
            latency_ms=latency_ms,
        )

    async def health_check(self) -> bool:
        return True
