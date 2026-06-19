from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import (
    CRITICAL_EVENTS,
    NotificationChannel,
    NotificationStatus,
    RETRY_DELAY_SCHEDULE,
    SkipReason,
)
from app.core.exceptions import (
    ChannelError,
    DNDRegisteredError,
    FrequencyCapExceeded,
    QuietHoursError,
)
from app.core.logging import get_logger
from app.models.notification import Notification
from app.redis.client import get_redis
from app.redis.frequency_cap import FrequencyCapService
from app.repositories.notification_repository import NotificationRepository
from app.repositories.user_repository import UserRepository
from app.services.compliance_service import ComplianceService

logger = get_logger(__name__)


class NotificationDispatcher:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.notification_repo = NotificationRepository(session)
        self.user_repo = UserRepository(session)

    async def dispatch(self, notification: Notification) -> None:
        if notification.status == NotificationStatus.SKIPPED:
            return

        user = await self.user_repo.get_with_preferences(notification.user_id)
        if not user:
            await self.notification_repo.update_status(
                notification.id,
                NotificationStatus.FAILED,
                {"error_message": "User not found"},
            )
            return

        preferences = user.preferences
        redis = await get_redis()
        freq_service = FrequencyCapService(redis)

        from app.redis.client import RedisCache
        cache = RedisCache(redis)
        compliance = ComplianceService(cache)

        # ── Compliance Checks ────────────────────────────────────────────────
        try:
            # Quiet hours
            if preferences and preferences.quiet_hours_enabled:
                await compliance.check_quiet_hours(
                    user_id=str(user.id),
                    event_type=notification.event_type,
                    quiet_hours_start=preferences.quiet_hours_start,
                    quiet_hours_end=preferences.quiet_hours_end,
                    timezone_str=user.timezone,
                )

            # DND check for SMS and WhatsApp
            if notification.channel in (NotificationChannel.SMS, NotificationChannel.WHATSAPP):
                if user.phone:
                    await compliance.check_dnd(user.phone, notification.event_type)

            # Frequency cap
            cap_hourly = preferences.frequency_cap_hourly if preferences else 0
            cap_daily = preferences.frequency_cap_daily if preferences else 0
            cap_weekly = preferences.frequency_cap_weekly if preferences else 0

            await freq_service.check_and_increment(
                user_id=str(user.id),
                channel=notification.channel,
                cap_hourly=cap_hourly or None,
                cap_daily=cap_daily or None,
                cap_weekly=cap_weekly or None,
            )

        except QuietHoursError:
            await self._skip(notification, SkipReason.QUIET_HOURS)
            return
        except DNDRegisteredError:
            await self._skip(notification, SkipReason.DND_REGISTERED)
            return
        except FrequencyCapExceeded:
            await self._skip(notification, SkipReason.FREQUENCY_CAPPED)
            return

        # ── Mark as queued & send via Celery ─────────────────────────────────
        await self.notification_repo.update_status(
            notification.id, NotificationStatus.QUEUED
        )

        from app.celery.tasks import send_notification_task
        send_notification_task.apply_async(
            args=[str(notification.id)],
            queue="notifications",
        )

        logger.info(
            "notification_queued",
            notification_id=str(notification.id),
            channel=notification.channel,
            event_type=notification.event_type,
        )

    async def _skip(self, notification: Notification, reason: SkipReason) -> None:
        await self.notification_repo.update_status(
            notification.id,
            NotificationStatus.SKIPPED,
            {"skip_reason": reason},
        )
        logger.info(
            "notification_skipped",
            notification_id=str(notification.id),
            reason=reason,
            channel=notification.channel,
        )
