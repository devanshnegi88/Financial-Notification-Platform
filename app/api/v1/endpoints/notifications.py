from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import (
    FinancialEventType,
    NotificationChannel,
    NotificationPriority,
    NotificationStatus,
    UserRole,
)
from app.db.base import get_db
from app.kafka.producer import NotificationEventProducer, get_producer
from app.middleware.auth_middleware import (
    CurrentUser,
    get_current_user,
    require_manager,
)
from app.repositories.notification_repository import NotificationRepository
from app.schemas.common import MessageResponse, PaginatedResponse, PaginationParams
from app.schemas.notification import (
    BulkEventRequest,
    MarkReadRequest,
    NotificationEventPayload,
    NotificationListResponse,
    NotificationResponse,
)

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.post("/events", response_model=MessageResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_event(
    payload: NotificationEventPayload,
    current_user: CurrentUser = Depends(require_manager),
):
    """Trigger a financial event that will generate notifications."""
    producer = await get_producer()
    event_producer = NotificationEventProducer(producer)

    await event_producer.publish_notification_event(
        payload=payload.model_dump(mode="json"),
        partition_key=str(payload.user_id),
    )
    return MessageResponse(message="Event accepted for processing", details={"user_id": str(payload.user_id)})


@router.post("/events/bulk", response_model=MessageResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_bulk_event(
    payload: BulkEventRequest,
    current_user: CurrentUser = Depends(require_manager),
):
    """Trigger same event for multiple users."""
    producer = await get_producer()
    event_producer = NotificationEventProducer(producer)

    for user_id in payload.user_ids:
        await event_producer.publish_notification_event(
            payload={
                "user_id": str(user_id),
                "event_type": payload.event_type,
                "priority": payload.priority,
                "channels": payload.channels,
                "event_data": payload.event_data,
            },
            partition_key=str(user_id),
        )

    return MessageResponse(
        message=f"Bulk event accepted for {len(payload.user_ids)} users",
        details={"count": len(payload.user_ids)},
    )


@router.get("/", response_model=PaginatedResponse[NotificationListResponse])
async def list_notifications(
    pagination: PaginationParams = Depends(),
    status: Optional[NotificationStatus] = Query(default=None),
    channel: Optional[NotificationChannel] = Query(default=None),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = NotificationRepository(db)
    items, total = await repo.get_user_notifications(
        user_id=current_user.user_id,
        skip=pagination.offset,
        limit=pagination.page_size,
        status=status,
        channel=channel,
    )
    return PaginatedResponse.build(
        items=[NotificationListResponse.model_validate(n) for n in items],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.get("/unread-count", response_model=dict)
async def get_unread_count(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = NotificationRepository(db)
    count = await repo.get_unread_count(current_user.user_id)
    return {"unread_count": count}


@router.get("/{notification_id}", response_model=NotificationResponse)
async def get_notification(
    notification_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = NotificationRepository(db)
    notification = await repo.get_with_delivery_logs(notification_id)
    if not notification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")

    if notification.user_id != current_user.user_id and current_user.role not in (
        UserRole.SUPERADMIN, UserRole.ADMIN, UserRole.MANAGER
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    return notification


@router.post("/mark-read", response_model=MessageResponse)
async def mark_notifications_read(
    payload: MarkReadRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = NotificationRepository(db)
    count = await repo.mark_as_read(payload.notification_ids, current_user.user_id)
    return MessageResponse(message=f"Marked {count} notification(s) as read")


@router.post("/{notification_id}/retry", response_model=MessageResponse)
async def retry_notification(
    notification_id: UUID,
    _: CurrentUser = Depends(require_manager),
    db: AsyncSession = Depends(get_db),
):
    repo = NotificationRepository(db)
    notification = await repo.get(notification_id)
    if not notification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")

    if notification.status not in (NotificationStatus.FAILED, NotificationStatus.DEAD):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only failed or dead notifications can be retried",
        )

    from app.celery.tasks import send_notification_task
    await repo.update_status(notification_id, NotificationStatus.PENDING, {"retry_count": 0})
    send_notification_task.apply_async(args=[str(notification_id)], queue="notifications")

    return MessageResponse(message="Notification queued for retry")


@router.delete("/{notification_id}", response_model=MessageResponse)
async def cancel_notification(
    notification_id: UUID,
    current_user: CurrentUser = Depends(require_manager),
    db: AsyncSession = Depends(get_db),
):
    repo = NotificationRepository(db)
    notification = await repo.get(notification_id)
    if not notification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")

    if notification.status in (NotificationStatus.DELIVERED, NotificationStatus.SENT):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel an already sent notification",
        )

    await repo.update_status(notification_id, NotificationStatus.CANCELLED)
    return MessageResponse(message="Notification cancelled")
