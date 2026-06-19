import hashlib
import hmac
from typing import Any, Dict

from fastapi import APIRouter, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from app.core.config import settings
from app.core.constants import DeliveryStatus
from app.core.logging import get_logger
from app.db.base import get_db
from app.services.delivery_tracking_service import DeliveryTrackingService

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])
logger = get_logger(__name__)


@router.post("/twilio/sms", status_code=status.HTTP_204_NO_CONTENT)
async def twilio_sms_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Twilio SMS delivery status callback."""
    form = await request.form()
    message_sid = form.get("MessageSid", "")
    message_status = form.get("MessageStatus", "").lower()
    error_code = form.get("ErrorCode")
    error_message = form.get("ErrorMessage")

    STATUS_MAP = {
        "delivered": DeliveryStatus.DELIVERED,
        "undelivered": DeliveryStatus.FAILED,
        "failed": DeliveryStatus.FAILED,
        "sent": DeliveryStatus.SENT,
        "queued": DeliveryStatus.QUEUED,
    }
    delivery_status = STATUS_MAP.get(message_status, DeliveryStatus.UNKNOWN)

    service = DeliveryTrackingService(db)
    await service.handle_delivery_receipt(
        provider="twilio",
        provider_message_id=message_sid,
        status=delivery_status,
        extra={
            "twilio_status": message_status,
            "error_code": error_code,
            "error_message": error_message,
        },
    )
    await db.commit()


@router.post("/sendgrid/email", status_code=status.HTTP_204_NO_CONTENT)
async def sendgrid_email_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """SendGrid email event webhook."""
    try:
        events = await request.json()
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON")

    service = DeliveryTrackingService(db)

    for event in events:
        event_type = event.get("event", "").lower()
        message_id = event.get("sg_message_id", "").split(".")[0]

        STATUS_MAP = {
            "delivered": DeliveryStatus.DELIVERED,
            "bounce": DeliveryStatus.BOUNCED,
            "open": DeliveryStatus.OPENED,
            "click": DeliveryStatus.CLICKED,
            "dropped": DeliveryStatus.FAILED,
            "spamreport": DeliveryStatus.FAILED,
            "unsubscribe": DeliveryStatus.FAILED,
        }
        delivery_status = STATUS_MAP.get(event_type)
        if delivery_status and message_id:
            await service.handle_delivery_receipt(
                provider="sendgrid",
                provider_message_id=message_id,
                status=delivery_status,
                extra={"sendgrid_event": event_type, "timestamp": event.get("timestamp")},
            )

    await db.commit()


@router.get("/delivery-timeline/{notification_id}", response_model=list)
async def get_delivery_timeline(
    notification_id: str,
    db: AsyncSession = Depends(get_db),
):
    from uuid import UUID
    service = DeliveryTrackingService(db)
    return await service.get_delivery_timeline(UUID(notification_id))
