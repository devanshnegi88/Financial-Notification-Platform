import time
from typing import Any, Dict, Optional

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Content, To

from app.channels.base import BaseChannel, ChannelResult
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class EmailChannel(BaseChannel):
    def __init__(self):
        self._client: Optional[SendGridAPIClient] = None

    @property
    def channel_name(self) -> str:
        return "email"

    def _get_client(self) -> SendGridAPIClient:
        if self._client is None:
            self._client = SendGridAPIClient(api_key=settings.SENDGRID_API_KEY)
        return self._client

    async def send(
        self,
        recipient: str,
        subject: Optional[str],
        body: str,
        html_body: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> ChannelResult:
        start = time.monotonic()
        try:
            message = Mail(
                from_email=(settings.SENDGRID_FROM_EMAIL, settings.SENDGRID_FROM_NAME),
                to_emails=recipient,
                subject=subject or "Notification",
            )

            if html_body:
                message.add_content(Content("text/html", html_body))
            message.add_content(Content("text/plain", body))

            if settings.SENDGRID_SANDBOX_MODE:
                message.mail_settings = {"sandbox_mode": {"enable": True}}

            client = self._get_client()
            response = client.send(message)
            latency_ms = int((time.monotonic() - start) * 1000)

            message_id = response.headers.get("X-Message-Id", "")
            success = response.status_code in (200, 202)

            logger.info(
                "email_sent",
                to=recipient,
                status_code=response.status_code,
                message_id=message_id,
                latency_ms=latency_ms,
            )
            return ChannelResult(
                success=success,
                provider_message_id=message_id,
                provider_response={"status_code": response.status_code},
                latency_ms=latency_ms,
            )

        except Exception as e:
            latency_ms = int((time.monotonic() - start) * 1000)
            logger.error("email_send_failed", to=recipient, error=str(e))
            return ChannelResult(
                success=False,
                error_message=str(e),
                latency_ms=latency_ms,
            )

    async def health_check(self) -> bool:
        try:
            client = self._get_client()
            response = client.client.suppression.bounces.get()
            return response.status_code == 200
        except Exception:
            return False
