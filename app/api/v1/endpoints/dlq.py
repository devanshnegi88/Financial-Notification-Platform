from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import NotificationStatus
from app.db.base import get_db
from app.middleware.auth_middleware import require_admin, require_analyst
from app.models.dead_letter_queue import DeadLetterQueue
from app.models.notification import Notification
from app.schemas.common import MessageResponse, PaginatedResponse, PaginationParams

router = APIRouter(prefix="/dlq", tags=["Dead Letter Queue"])


class DLQEntryResponse(BaseModel):
    id: UUID
    notification_id: UUID
    failure_reason: str
    retry_count: int
    last_error: Optional[str]
    resolved: bool
    resolved_by: Optional[str]
    resolved_at: Optional[datetime]
    resolution_action: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class DLQResolveRequest(BaseModel):
    resolution_action: str  # retried | discarded | manual_send
    resolved_by: str
    notes: Optional[str] = None


@router.get("/", response_model=PaginatedResponse[DLQEntryResponse])
async def list_dlq_entries(
    pagination: PaginationParams = Depends(),
    resolved: Optional[bool] = Query(default=False),
    failure_reason: Optional[str] = Query(default=None),
    _=Depends(require_analyst),
    db: AsyncSession = Depends(get_db),
):
    """List Dead Letter Queue entries with filtering."""
    query = select(DeadLetterQueue)
    count_q = select(func.count()).select_from(DeadLetterQueue)

    filters = [DeadLetterQueue.resolved == resolved]
    if failure_reason:
        filters.append(DeadLetterQueue.failure_reason.ilike(f"%{failure_reason}%"))

    query = query.where(and_(*filters))
    count_q = count_q.where(and_(*filters))
    query = (
        query.order_by(DeadLetterQueue.created_at.desc())
        .offset(pagination.offset)
        .limit(pagination.page_size)
    )

    items_result = await db.execute(query)
    count_result = await db.execute(count_q)
    items = list(items_result.scalars().all())
    total = count_result.scalar_one()

    return PaginatedResponse.build(
        items=[DLQEntryResponse.model_validate(e) for e in items],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.get("/stats", response_model=dict)
async def get_dlq_stats(
    _=Depends(require_analyst),
    db: AsyncSession = Depends(get_db),
):
    """Get DLQ depth and breakdown statistics."""
    total = await db.scalar(select(func.count()).select_from(DeadLetterQueue))
    unresolved = await db.scalar(
        select(func.count()).select_from(DeadLetterQueue).where(DeadLetterQueue.resolved == False)
    )
    resolved = await db.scalar(
        select(func.count()).select_from(DeadLetterQueue).where(DeadLetterQueue.resolved == True)
    )

    # Breakdown by failure reason
    reason_result = await db.execute(
        select(DeadLetterQueue.failure_reason, func.count().label("count"))
        .where(DeadLetterQueue.resolved == False)
        .group_by(DeadLetterQueue.failure_reason)
        .order_by(func.count().desc())
        .limit(10)
    )
    by_reason = [{"reason": row.failure_reason, "count": row.count} for row in reason_result.all()]

    return {
        "total": total,
        "unresolved": unresolved,
        "resolved": resolved,
        "by_reason": by_reason,
        "alert": unresolved > 100,  # per spec A11.2 HighDLQDepth alert threshold
    }


@router.get("/{dlq_id}", response_model=DLQEntryResponse)
async def get_dlq_entry(
    dlq_id: UUID,
    _=Depends(require_analyst),
    db: AsyncSession = Depends(get_db),
):
    entry = await db.get(DeadLetterQueue, dlq_id)
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DLQ entry not found")
    return entry


@router.post("/{dlq_id}/retry", response_model=MessageResponse)
async def retry_dlq_entry(
    dlq_id: UUID,
    _=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Re-queue a DLQ notification for delivery."""
    entry = await db.get(DeadLetterQueue, dlq_id)
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DLQ entry not found")
    if entry.resolved:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Entry already resolved")

    # Reset notification and re-queue
    notification = await db.get(Notification, entry.notification_id)
    if notification:
        notification.status = NotificationStatus.PENDING
        notification.retry_count = 0
        notification.error_message = None
        db.add(notification)

    entry.resolved = True
    entry.resolution_action = "retried"
    entry.resolved_at = datetime.now(timezone.utc)
    db.add(entry)
    await db.flush()

    from app.celery.tasks import send_notification_task
    send_notification_task.apply_async(
        args=[str(entry.notification_id)], queue="notifications"
    )

    return MessageResponse(
        message="DLQ entry re-queued for delivery",
        details={"notification_id": str(entry.notification_id)},
    )


@router.post("/{dlq_id}/discard", response_model=MessageResponse)
async def discard_dlq_entry(
    dlq_id: UUID,
    payload: DLQResolveRequest,
    _=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Mark a DLQ entry as discarded (permanent failure)."""
    entry = await db.get(DeadLetterQueue, dlq_id)
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DLQ entry not found")
    if entry.resolved:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Entry already resolved")

    entry.resolved = True
    entry.resolution_action = "discarded"
    entry.resolved_by = payload.resolved_by
    entry.resolved_at = datetime.now(timezone.utc)
    db.add(entry)
    await db.flush()

    return MessageResponse(message="DLQ entry discarded", details={"notes": payload.notes})


@router.post("/bulk-retry", response_model=MessageResponse)
async def bulk_retry_dlq(
    reason_filter: Optional[str] = Query(default=None),
    _=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Bulk retry all unresolved DLQ entries (optionally filtered by reason)."""
    query = select(DeadLetterQueue).where(DeadLetterQueue.resolved == False)
    if reason_filter:
        query = query.where(DeadLetterQueue.failure_reason.ilike(f"%{reason_filter}%"))

    result = await db.execute(query.limit(500))
    entries = result.scalars().all()

    from app.celery.tasks import send_notification_task
    count = 0
    for entry in entries:
        notification = await db.get(Notification, entry.notification_id)
        if notification:
            notification.status = NotificationStatus.PENDING
            notification.retry_count = 0
            db.add(notification)

        entry.resolved = True
        entry.resolution_action = "retried"
        entry.resolved_at = datetime.now(timezone.utc)
        db.add(entry)

        send_notification_task.apply_async(
            args=[str(entry.notification_id)], queue="notifications"
        )
        count += 1

    await db.flush()
    return MessageResponse(message=f"Bulk retried {count} DLQ entries")
