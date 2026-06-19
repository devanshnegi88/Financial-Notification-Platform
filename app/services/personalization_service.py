from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import FinancialEventType, NotificationChannel, NotificationStatus
from app.core.logging import get_logger
from app.models.notification import Notification
from app.models.user import User

logger = get_logger(__name__)


class PersonalizationService:
    """
    Enriches notification context with personalized data derived from
    user history, preferences, and behaviour patterns.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def enrich_context(
        self,
        user_id: UUID,
        event_type: FinancialEventType,
        channel: NotificationChannel,
        base_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        context = {**base_context}

        user_result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        user = user_result.scalar_one_or_none()
        if not user:
            return context

        context["user_name"] = user.full_name
        context["user_email"] = user.email
        context["locale"] = user.locale.value if hasattr(user.locale, "value") else user.locale

        # Attach channel-specific engagement signals
        engagement = await self._get_engagement_stats(user_id, channel)
        context["_engagement"] = engagement

        # Preferred time hint (for scheduling)
        context["_preferred_hour"] = await self._get_preferred_send_hour(user_id, channel)

        return context

    async def _get_engagement_stats(
        self, user_id: UUID, channel: NotificationChannel
    ) -> Dict[str, Any]:
        result = await self.session.execute(
            select(
                func.count().label("total"),
                func.sum(
                    func.cast(Notification.read_at.isnot(None), func.Integer)
                ).label("read_count"),
                func.sum(
                    func.cast(Notification.status == NotificationStatus.DELIVERED, func.Integer)
                ).label("delivered_count"),
            )
            .where(
                and_(
                    Notification.user_id == user_id,
                    Notification.channel == channel,
                )
            )
        )
        row = result.first()
        total = row.total or 0
        delivered = row.delivered_count or 0
        read = row.read_count or 0
        return {
            "total_received": total,
            "delivery_rate": round(delivered / total * 100, 1) if total > 0 else 0.0,
            "read_rate": round(read / delivered * 100, 1) if delivered > 0 else 0.0,
        }

    async def _get_preferred_send_hour(
        self, user_id: UUID, channel: NotificationChannel
    ) -> Optional[int]:
        """Returns the hour (0-23) when the user most often reads notifications."""
        result = await self.session.execute(
            select(
                func.extract("hour", Notification.read_at).label("hour"),
                func.count().label("count"),
            )
            .where(
                and_(
                    Notification.user_id == user_id,
                    Notification.channel == channel,
                    Notification.read_at.isnot(None),
                )
            )
            .group_by(func.extract("hour", Notification.read_at))
            .order_by(func.count().desc())
            .limit(1)
        )
        row = result.first()
        return int(row.hour) if row else None

    async def get_optimal_channel(
        self,
        user_id: UUID,
        available_channels: list[NotificationChannel],
    ) -> NotificationChannel:
        """Returns the channel with highest delivery+read rate for this user."""
        if not available_channels:
            return NotificationChannel.IN_APP

        best_channel = available_channels[0]
        best_score = -1.0

        for channel in available_channels:
            stats = await self._get_engagement_stats(user_id, channel)
            score = (stats["delivery_rate"] * 0.6) + (stats["read_rate"] * 0.4)
            if score > best_score:
                best_score = score
                best_channel = channel

        logger.info(
            "optimal_channel_selected",
            user_id=str(user_id),
            channel=best_channel,
            score=best_score,
        )
        return best_channel
