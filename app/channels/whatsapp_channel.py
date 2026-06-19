import time
from typing import Any, Dict, Optional

from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client

from app.channels.base import BaseChannel, ChannelResult
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class WhatsAppChannel(BaseChannel):
    def __init__(self):
        self._client: Optional[Client] = None

    @property
    def channel_name(self) -> str:
        return "whatsapp"

    def _get_client(self) -> Client:
        if self._client is None:
            self._client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
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
            client = self._get_client()
            wa_to = recipient if recipient.startswith("whatsapp:") else f"whatsapp:{recipient}"

            message = client.messages.create(
                body=body,
                from_=settings.TWILIO_WHATSAPP_FROM,
                to=wa_to,
            )
            latency_ms = int((time.monotonic() - start) * 1000)

            logger.info(
                "whatsapp_sent",
                to=recipient,
                sid=message.sid,
                status=message.status,
                latency_ms=latency_ms,
            )
            return ChannelResult(
                success=True,
                provider_message_id=message.sid,
                provider_response={"status": message.status, "sid": message.sid},
                latency_ms=latency_ms,
            )

        except TwilioRestException as e:
            latency_ms = int((time.monotonic() - start) * 1000)
            logger.error("whatsapp_send_failed", to=recipient, error=str(e), code=e.code)
            return ChannelResult(
                success=False,
                error_message=str(e),
                error_code=str(e.code),
                latency_ms=latency_ms,
            )
        except Exception as e:
            latency_ms = int((time.monotonic() - start) * 1000)
            logger.error("whatsapp_send_error", to=recipient, error=str(e))
            return ChannelResult(
                success=False,
                error_message=str(e),
                latency_ms=latency_ms,
            )

    async def health_check(self) -> bool:
        try:
            client = self._get_client()
            client.api.accounts(settings.TWILIO_ACCOUNT_SID).fetch()
            return True
        except Exception:
            return False
