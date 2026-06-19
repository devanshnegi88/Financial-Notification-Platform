from datetime import date, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import FinancialEventType, NotificationChannel
from app.db.base import get_db
from app.middleware.auth_middleware import require_analyst
from app.schemas.analytics import AnalyticsDashboard, AnalyticsSummary
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/dashboard", response_model=AnalyticsDashboard)
async def get_dashboard(
    from_date: date = Query(default_factory=lambda: date.today() - timedelta(days=30)),
    to_date: date = Query(default_factory=date.today),
    _=Depends(require_analyst),
    db: AsyncSession = Depends(get_db),
):
    service = AnalyticsService(db)
    return await service.get_dashboard(from_date, to_date)


@router.get("/summary", response_model=List[AnalyticsSummary])
async def get_summary(
    from_date: date = Query(default_factory=lambda: date.today() - timedelta(days=7)),
    to_date: date = Query(default_factory=date.today),
    event_type: Optional[FinancialEventType] = Query(default=None),
    channel: Optional[NotificationChannel] = Query(default=None),
    _=Depends(require_analyst),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import and_, select
    from app.models.analytics import NotificationAnalytics

    query = select(NotificationAnalytics).where(
        and_(
            NotificationAnalytics.date >= from_date,
            NotificationAnalytics.date <= to_date,
        )
    )
    if event_type:
        query = query.where(NotificationAnalytics.event_type == event_type)
    if channel:
        query = query.where(NotificationAnalytics.channel == channel)

    query = query.order_by(NotificationAnalytics.date.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


@router.post("/aggregate", response_model=dict)
async def trigger_aggregation(
    target_date: date = Query(default_factory=lambda: date.today() - timedelta(days=1)),
    _=Depends(require_analyst),
    db: AsyncSession = Depends(get_db),
):
    service = AnalyticsService(db)
    await service.upsert_daily_aggregates(target_date)
    return {"message": f"Analytics aggregated for {target_date}", "date": str(target_date)}


@router.get("/channel-performance", response_model=List[dict])
async def get_channel_performance(
    from_date: date = Query(default_factory=lambda: date.today() - timedelta(days=30)),
    to_date: date = Query(default_factory=date.today),
    _=Depends(require_analyst),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import and_, func, select
    from app.models.analytics import NotificationAnalytics

    result = await db.execute(
        select(
            NotificationAnalytics.channel,
            func.sum(NotificationAnalytics.total_sent).label("total_sent"),
            func.sum(NotificationAnalytics.total_delivered).label("total_delivered"),
            func.sum(NotificationAnalytics.total_failed).label("total_failed"),
            func.sum(NotificationAnalytics.total_skipped).label("total_skipped"),
            func.avg(NotificationAnalytics.delivery_rate).label("avg_delivery_rate"),
            func.avg(NotificationAnalytics.avg_latency_ms).label("avg_latency_ms"),
        )
        .where(
            and_(
                NotificationAnalytics.date >= from_date,
                NotificationAnalytics.date <= to_date,
            )
        )
        .group_by(NotificationAnalytics.channel)
    )
    return [
        {
            "channel": row.channel,
            "total_sent": row.total_sent or 0,
            "total_delivered": row.total_delivered or 0,
            "total_failed": row.total_failed or 0,
            "total_skipped": row.total_skipped or 0,
            "avg_delivery_rate": round(float(row.avg_delivery_rate or 0), 2),
            "avg_latency_ms": round(float(row.avg_latency_ms or 0), 2),
        }
        for row in result.all()
    ]


@router.get("/event-performance", response_model=List[dict])
async def get_event_performance(
    from_date: date = Query(default_factory=lambda: date.today() - timedelta(days=30)),
    to_date: date = Query(default_factory=date.today),
    _=Depends(require_analyst),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import and_, func, select
    from app.models.analytics import NotificationAnalytics

    result = await db.execute(
        select(
            NotificationAnalytics.event_type,
            func.sum(NotificationAnalytics.total_sent).label("total_sent"),
            func.sum(NotificationAnalytics.total_delivered).label("total_delivered"),
            func.sum(NotificationAnalytics.total_failed).label("total_failed"),
            func.avg(NotificationAnalytics.delivery_rate).label("avg_delivery_rate"),
        )
        .where(
            and_(
                NotificationAnalytics.date >= from_date,
                NotificationAnalytics.date <= to_date,
            )
        )
        .group_by(NotificationAnalytics.event_type)
        .order_by(func.sum(NotificationAnalytics.total_sent).desc())
    )
    return [
        {
            "event_type": row.event_type,
            "total_sent": row.total_sent or 0,
            "total_delivered": row.total_delivered or 0,
            "total_failed": row.total_failed or 0,
            "avg_delivery_rate": round(float(row.avg_delivery_rate or 0), 2),
        }
        for row in result.all()
    ]


@router.get("/skip-analysis", response_model=List[dict])
async def get_skip_analysis(
    from_date: date = Query(default_factory=lambda: date.today() - timedelta(days=30)),
    to_date: date = Query(default_factory=date.today),
    _=Depends(require_analyst),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import and_, func, select
    from app.models.analytics import NotificationAnalytics

    result = await db.execute(
        select(
            NotificationAnalytics.date,
            func.sum(NotificationAnalytics.skip_dnd).label("skip_dnd"),
            func.sum(NotificationAnalytics.skip_quiet_hours).label("skip_quiet_hours"),
            func.sum(NotificationAnalytics.skip_frequency_cap).label("skip_frequency_cap"),
            func.sum(NotificationAnalytics.skip_user_opt_out).label("skip_user_opt_out"),
        )
        .where(
            and_(
                NotificationAnalytics.date >= from_date,
                NotificationAnalytics.date <= to_date,
            )
        )
        .group_by(NotificationAnalytics.date)
        .order_by(NotificationAnalytics.date)
    )
    return [
        {
            "date": str(row.date),
            "skip_dnd": row.skip_dnd or 0,
            "skip_quiet_hours": row.skip_quiet_hours or 0,
            "skip_frequency_cap": row.skip_frequency_cap or 0,
            "skip_user_opt_out": row.skip_user_opt_out or 0,
        }
        for row in result.all()
    ]
