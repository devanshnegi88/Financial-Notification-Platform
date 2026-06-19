from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import FinancialEventType, NotificationChannel, NotificationStatus
from app.core.logging import get_logger
from app.models.analytics import NotificationAnalytics
from app.models.notification import Notification
from app.schemas.analytics import AnalyticsDashboard

logger = get_logger(__name__)


class AnalyticsService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_dashboard(self, from_date: date, to_date: date) -> AnalyticsDashboard:
        from_dt = datetime.combine(from_date, datetime.min.time())
        to_dt = datetime.combine(to_date, datetime.max.time())

        # Total counts by status
        status_result = await self.session.execute(
            select(Notification.status, func.count().label("count"))
            .where(and_(Notification.created_at >= from_dt, Notification.created_at <= to_dt))
            .group_by(Notification.status)
        )
        by_status = [{"status": row.status, "count": row.count} for row in status_result.all()]

        total = sum(r["count"] for r in by_status)
        delivered = next((r["count"] for r in by_status if r["status"] == NotificationStatus.DELIVERED), 0)
        failed = next((r["count"] for r in by_status if r["status"] == NotificationStatus.FAILED), 0)
        skipped = next((r["count"] for r in by_status if r["status"] == NotificationStatus.SKIPPED), 0)
        delivery_rate = round((delivered / total * 100), 2) if total > 0 else 0.0

        # By channel
        channel_result = await self.session.execute(
            select(Notification.channel, func.count().label("count"))
            .where(and_(Notification.created_at >= from_dt, Notification.created_at <= to_dt))
            .group_by(Notification.channel)
        )
        by_channel = [{"channel": row.channel, "count": row.count} for row in channel_result.all()]

        # By event type
        event_result = await self.session.execute(
            select(Notification.event_type, func.count().label("count"))
            .where(and_(Notification.created_at >= from_dt, Notification.created_at <= to_dt))
            .group_by(Notification.event_type)
            .order_by(func.count().desc())
            .limit(10)
        )
        by_event_type = [{"event_type": row.event_type, "count": row.count} for row in event_result.all()]

        # Daily trend
        daily_result = await self.session.execute(
            select(
                func.date(Notification.created_at).label("date"),
                func.count().label("total"),
                func.sum(
                    func.cast(Notification.status == NotificationStatus.DELIVERED, func.Integer)
                ).label("delivered"),
            )
            .where(and_(Notification.created_at >= from_dt, Notification.created_at <= to_dt))
            .group_by(func.date(Notification.created_at))
            .order_by(func.date(Notification.created_at))
        )
        daily_trend = [
            {"date": str(row.date), "total": row.total, "delivered": row.delivered or 0}
            for row in daily_result.all()
        ]

        return AnalyticsDashboard(
            total_notifications=total,
            total_delivered=delivered,
            total_failed=failed,
            total_skipped=skipped,
            delivery_rate=delivery_rate,
            by_channel=by_channel,
            by_event_type=by_event_type,
            by_status=by_status,
            daily_trend=daily_trend,
        )

    async def upsert_daily_aggregates(self, target_date: date) -> None:
        from_dt = datetime.combine(target_date, datetime.min.time())
        to_dt = datetime.combine(target_date, datetime.max.time())

        rows = await self.session.execute(
            select(
                Notification.event_type,
                Notification.channel,
                Notification.status,
                Notification.skip_reason,
                func.count().label("count"),
                func.avg(
                    func.extract("epoch", Notification.sent_at - Notification.created_at) * 1000
                ).label("avg_latency_ms"),
            )
            .where(and_(Notification.created_at >= from_dt, Notification.created_at <= to_dt))
            .group_by(Notification.event_type, Notification.channel, Notification.status, Notification.skip_reason)
        )

        aggregates: Dict[tuple, Dict[str, Any]] = {}
        for row in rows.all():
            key = (row.event_type, row.channel)
            if key not in aggregates:
                aggregates[key] = {
                    "date": target_date,
                    "event_type": row.event_type,
                    "channel": row.channel,
                    "total_sent": 0,
                    "total_delivered": 0,
                    "total_failed": 0,
                    "total_skipped": 0,
                    "total_retried": 0,
                    "total_dead": 0,
                    "skip_dnd": 0,
                    "skip_quiet_hours": 0,
                    "skip_frequency_cap": 0,
                    "skip_user_opt_out": 0,
                    "avg_latency_ms": 0,
                }

            agg = aggregates[key]
            if row.status == NotificationStatus.SENT:
                agg["total_sent"] += row.count
            elif row.status == NotificationStatus.DELIVERED:
                agg["total_delivered"] += row.count
                agg["total_sent"] += row.count
            elif row.status == NotificationStatus.FAILED:
                agg["total_failed"] += row.count
            elif row.status == NotificationStatus.SKIPPED:
                agg["total_skipped"] += row.count
                from app.core.constants import SkipReason
                if row.skip_reason == SkipReason.DND_REGISTERED:
                    agg["skip_dnd"] += row.count
                elif row.skip_reason == SkipReason.QUIET_HOURS:
                    agg["skip_quiet_hours"] += row.count
                elif row.skip_reason == SkipReason.FREQUENCY_CAPPED:
                    agg["skip_frequency_cap"] += row.count
                elif row.skip_reason == SkipReason.USER_OPT_OUT:
                    agg["skip_user_opt_out"] += row.count
            elif row.status == NotificationStatus.RETRYING:
                agg["total_retried"] += row.count
            elif row.status == NotificationStatus.DEAD:
                agg["total_dead"] += row.count

            if row.avg_latency_ms:
                agg["avg_latency_ms"] = float(row.avg_latency_ms)

        for (event_type, channel), data in aggregates.items():
            total = data["total_sent"] + data["total_failed"] + data["total_skipped"]
            data["delivery_rate"] = round(data["total_delivered"] / total * 100, 2) if total > 0 else None

            existing = await self.session.execute(
                select(NotificationAnalytics).where(
                    and_(
                        NotificationAnalytics.date == target_date,
                        NotificationAnalytics.event_type == event_type,
                        NotificationAnalytics.channel == channel,
                    )
                )
            )
            record = existing.scalar_one_or_none()
            if record:
                for k, v in data.items():
                    setattr(record, k, v)
                self.session.add(record)
            else:
                self.session.add(NotificationAnalytics(**data))

        await self.session.flush()
        logger.info("analytics_aggregates_updated", date=str(target_date), records=len(aggregates))
