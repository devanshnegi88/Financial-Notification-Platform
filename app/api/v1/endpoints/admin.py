from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.channels.channel_registry import health_check_all
from app.core.constants import NotificationStatus, UserRole
from app.db.base import get_db
from app.middleware.auth_middleware import CurrentUser, require_admin, require_superadmin
from app.schemas.common import MessageResponse
from app.schemas.user import UserCreate, UserResponse

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/health/channels", response_model=Dict[str, bool])
async def channel_health_check(_=Depends(require_admin)):
    return await health_check_all()


@router.get("/stats/overview", response_model=Dict[str, Any])
async def get_overview_stats(
    _=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import func, select
    from app.models.notification import Notification
    from app.models.user import User

    now = datetime.now(timezone.utc)
    last_24h = now - timedelta(hours=24)
    last_7d = now - timedelta(days=7)

    total_users = await db.scalar(select(func.count()).select_from(User))
    active_users = await db.scalar(
        select(func.count()).select_from(User).where(User.is_active == True)
    )

    total_notifications_24h = await db.scalar(
        select(func.count()).select_from(Notification).where(Notification.created_at >= last_24h)
    )
    delivered_24h = await db.scalar(
        select(func.count()).select_from(Notification).where(
            Notification.created_at >= last_24h,
            Notification.status == NotificationStatus.DELIVERED,
        )
    )
    failed_24h = await db.scalar(
        select(func.count()).select_from(Notification).where(
            Notification.created_at >= last_24h,
            Notification.status == NotificationStatus.FAILED,
        )
    )
    dead_24h = await db.scalar(
        select(func.count()).select_from(Notification).where(
            Notification.created_at >= last_24h,
            Notification.status == NotificationStatus.DEAD,
        )
    )

    return {
        "users": {"total": total_users, "active": active_users},
        "notifications_last_24h": {
            "total": total_notifications_24h,
            "delivered": delivered_24h,
            "failed": failed_24h,
            "dead": dead_24h,
            "delivery_rate": round(
                (delivered_24h / total_notifications_24h * 100), 2
            ) if total_notifications_24h else 0,
        },
        "timestamp": now.isoformat(),
    }


@router.post("/users/superadmin", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_admin_user(
    payload: UserCreate,
    _=Depends(require_superadmin),
    db: AsyncSession = Depends(get_db),
):
    from app.core.exceptions import ConflictError
    from app.services.auth_service import AuthService

    service = AuthService(db)
    try:
        user = await service.register(
            email=payload.email,
            password=payload.password,
            full_name=payload.full_name,
            phone=payload.phone,
            role=UserRole.ADMIN,
        )
        return user
    except ConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=e.message)


@router.post("/notifications/broadcast", response_model=MessageResponse)
async def broadcast_notification(
    event_type: str,
    message: str,
    _=Depends(require_superadmin),
    db: AsyncSession = Depends(get_db),
):
    """Send a notification to all active users."""
    from sqlalchemy import select
    from app.models.user import User
    from app.kafka.producer import NotificationEventProducer, get_producer
    from app.core.constants import FinancialEventType, NotificationPriority

    result = await db.execute(select(User.id).where(User.is_active == True))
    user_ids = [row[0] for row in result.all()]

    producer = await get_producer()
    event_producer = NotificationEventProducer(producer)

    count = 0
    for user_id in user_ids:
        await event_producer.publish_notification_event(
            payload={
                "user_id": str(user_id),
                "event_type": event_type,
                "priority": NotificationPriority.MEDIUM,
                "event_data": {"message": message},
            },
            partition_key=str(user_id),
        )
        count += 1

    return MessageResponse(
        message=f"Broadcast sent to {count} users",
        details={"user_count": count, "event_type": event_type},
    )


@router.delete("/notifications/dead-letters", response_model=MessageResponse)
async def purge_dead_letters(
    _=Depends(require_superadmin),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import delete
    from app.models.notification import Notification

    result = await db.execute(
        delete(Notification).where(Notification.status == NotificationStatus.DEAD)
    )
    return MessageResponse(message=f"Purged {result.rowcount} dead letter notifications")


@router.post("/cache/flush", response_model=MessageResponse)
async def flush_cache(_=Depends(require_superadmin)):
    from app.redis.client import get_redis

    redis = await get_redis()
    await redis.flushdb()
    return MessageResponse(message="Cache flushed successfully")
