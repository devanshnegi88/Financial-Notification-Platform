from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.constants import NotificationChannel, NotificationStatus, FinancialEventType
from app.models.delivery_log import DeliveryLog
from app.models.notification import Notification
from app.repositories.base import BaseRepository


class NotificationRepository(BaseRepository[Notification]):
    def __init__(self, session: AsyncSession):
        super().__init__(Notification, session)

    async def get_by_idempotency_key(self, key: str) -> Optional[Notification]:
        result = await self.session.execute(
            select(Notification).where(Notification.idempotency_key == key)
        )
        return result.scalar_one_or_none()

    async def get_with_delivery_logs(self, notification_id: UUID) -> Optional[Notification]:
        result = await self.session.execute(
            select(Notification)
            .options(selectinload(Notification.delivery_logs))
            .where(Notification.id == notification_id)
        )
        return result.scalar_one_or_none()

    async def get_pending_retries(self, limit: int = 100) -> List[Notification]:
        now = datetime.utcnow()
        result = await self.session.execute(
            select(Notification)
            .where(
                and_(
                    Notification.status == NotificationStatus.RETRYING,
                    Notification.next_retry_at <= now,
                    Notification.retry_count < Notification.max_retries,
                )
            )
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_user_notifications(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 20,
        status: Optional[NotificationStatus] = None,
        channel: Optional[NotificationChannel] = None,
    ) -> tuple[List[Notification], int]:
        query = select(Notification).where(Notification.user_id == user_id)
        count_query = select(func.count()).select_from(Notification).where(Notification.user_id == user_id)

        if status:
            query = query.where(Notification.status == status)
            count_query = count_query.where(Notification.status == status)
        if channel:
            query = query.where(Notification.channel == channel)
            count_query = count_query.where(Notification.channel == channel)

        query = query.order_by(Notification.created_at.desc()).offset(skip).limit(limit)

        items_result = await self.session.execute(query)
        count_result = await self.session.execute(count_query)

        return list(items_result.scalars().all()), count_result.scalar_one()

    async def get_unread_count(self, user_id: UUID) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(Notification).where(
                and_(
                    Notification.user_id == user_id,
                    Notification.channel == NotificationChannel.IN_APP,
                    Notification.read_at.is_(None),
                    Notification.status == NotificationStatus.DELIVERED,
                )
            )
        )
        return result.scalar_one()

    async def mark_as_read(self, notification_ids: List[UUID], user_id: UUID) -> int:
        now = datetime.utcnow()
        result = await self.session.execute(
            update(Notification)
            .where(
                and_(
                    Notification.id.in_(notification_ids),
                    Notification.user_id == user_id,
                    Notification.read_at.is_(None),
                )
            )
            .values(read_at=now)
        )
        return result.rowcount

    async def update_status(
        self,
        notification_id: UUID,
        status: NotificationStatus,
        extra: Optional[dict] = None,
    ) -> Optional[Notification]:
        values = {"status": status}
        if extra:
            values.update(extra)
        await self.session.execute(
            update(Notification).where(Notification.id == notification_id).values(**values)
        )
        return await self.get(notification_id)

    async def add_delivery_log(self, log_data: dict) -> DeliveryLog:
        log = DeliveryLog(**log_data)
        self.session.add(log)
        await self.session.flush()
        return log

    async def get_analytics_aggregates(
        self,
        from_date: datetime,
        to_date: datetime,
        event_type: Optional[FinancialEventType] = None,
        channel: Optional[NotificationChannel] = None,
    ) -> List[dict]:
        query = (
            select(
                func.date(Notification.created_at).label("date"),
                Notification.event_type,
                Notification.channel,
                Notification.status,
                func.count().label("count"),
            )
            .where(
                and_(
                    Notification.created_at >= from_date,
                    Notification.created_at <= to_date,
                )
            )
            .group_by(
                func.date(Notification.created_at),
                Notification.event_type,
                Notification.channel,
                Notification.status,
            )
        )
        if event_type:
            query = query.where(Notification.event_type == event_type)
        if channel:
            query = query.where(Notification.channel == channel)

        result = await self.session.execute(query)
        return [row._asdict() for row in result.all()]
