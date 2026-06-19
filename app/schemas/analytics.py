from datetime import date
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel

from app.core.constants import FinancialEventType, NotificationChannel


class AnalyticsSummary(BaseModel):
    date: date
    event_type: FinancialEventType
    channel: NotificationChannel
    total_sent: int
    total_delivered: int
    total_failed: int
    total_skipped: int
    total_retried: int
    total_dead: int
    total_opened: int
    total_clicked: int
    skip_dnd: int
    skip_quiet_hours: int
    skip_frequency_cap: int
    skip_user_opt_out: int
    avg_latency_ms: Optional[float]
    delivery_rate: Optional[float]
    open_rate: Optional[float]
    click_rate: Optional[float]

    model_config = {"from_attributes": True}


class AnalyticsDashboard(BaseModel):
    total_notifications: int
    total_delivered: int
    total_failed: int
    total_skipped: int
    delivery_rate: float
    by_channel: List[dict]
    by_event_type: List[dict]
    by_status: List[dict]
    daily_trend: List[dict]


class AnalyticsFilter(BaseModel):
    from_date: date
    to_date: date
    event_type: Optional[FinancialEventType] = None
    channel: Optional[NotificationChannel] = None
