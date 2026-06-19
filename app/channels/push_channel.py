import time
from typing import Any, Dict, List, Optional

import firebase_admin
from firebase_admin import credentials, messaging
from firebase_admin.exceptions import FirebaseError

from app.channels.base import BaseChannel, ChannelResult
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_firebase_initialized = False


def _init_firebase() -> None:
    global _firebase_initialized
    if not _firebase_initialized:
        try:
            cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
            firebase_admin.initialize_app(cred)
            _firebase_initialized = True
            logger.info("firebase_initialized")
        except Exception as e:
            logger.error("firebase_init_failed", error=str(e))


class PushChannel(BaseChannel):
    def __init__(self):
        _init_firebase()

    @property
    def channel_name(self) -> str:
        return "push"

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
            notification = messaging.Notification(
                title=subject or "Notification",
                body=body,
            )

            android_config = messaging.AndroidConfig(
                priority="high",
                notification=messaging.AndroidNotification(
                    sound="default",
                    click_action="FLUTTER_NOTIFICATION_CLICK",
                ),
            )
            apns_config = messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(sound="default", badge=1)
                )
            )

            data_payload = extra or {}

            message = messaging.Message(
                notification=notification,
                android=android_config,
                apns=apns_config,
                token=recipient,
                data={k: str(v) for k, v in data_payload.items()},
            )

            response = messaging.send(message)
            latency_ms = int((time.monotonic() - start) * 1000)

            logger.info("push_sent", token_prefix=recipient[:20], message_id=response, latency_ms=latency_ms)
            return ChannelResult(
                success=True,
                provider_message_id=response,
                provider_response={"message_id": response},
                latency_ms=latency_ms,
            )

        except FirebaseError as e:
            latency_ms = int((time.monotonic() - start) * 1000)
            logger.error("push_send_failed", error=str(e), code=e.code)
            return ChannelResult(
                success=False,
                error_message=str(e),
                error_code=str(e.code),
                latency_ms=latency_ms,
            )
        except Exception as e:
            latency_ms = int((time.monotonic() - start) * 1000)
            logger.error("push_send_error", error=str(e))
            return ChannelResult(
                success=False,
                error_message=str(e),
                latency_ms=latency_ms,
            )

    async def send_multicast(
        self,
        tokens: List[str],
        subject: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        try:
            message = messaging.MulticastMessage(
                notification=messaging.Notification(title=subject, body=body),
                tokens=tokens,
                data={k: str(v) for k, v in (data or {}).items()},
            )
            response = messaging.send_each_for_multicast(message)
            return {
                "success_count": response.success_count,
                "failure_count": response.failure_count,
            }
        except Exception as e:
            logger.error("push_multicast_failed", error=str(e))
            return {"success_count": 0, "failure_count": len(tokens), "error": str(e)}

    async def health_check(self) -> bool:
        return _firebase_initialized
