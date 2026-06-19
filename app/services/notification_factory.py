from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.constants import (
    CHANNEL_PRIORITY_MAP,
    CRITICAL_EVENTS,
    DND_EXEMPT_EVENTS,
    CHANNEL_MAX_RETRIES,
    FinancialEventType,
    NotificationChannel,
    NotificationPriority,
    NotificationStatus,
    SkipReason,
)
from app.core.logging import get_logger
from app.models.notification import Notification
from app.repositories.notification_repository import NotificationRepository
from app.repositories.template_repository import TemplateRepository
from app.repositories.user_repository import UserRepository
from app.services.compliance_service import ComplianceService
from app.services.template_service import TemplateService

logger = get_logger(__name__)


class NotificationFactory:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)
        self.notification_repo = NotificationRepository(session)
        self.template_repo = TemplateRepository(session)
        self.template_service = TemplateService(session)
        self.compliance_service = ComplianceService()

    async def build_notifications(
        self,
        user_id: UUID,
        event_type: str,
        priority: str = "medium",
        channels: Optional[List[str]] = None,
        event_data: Optional[Dict[str, Any]] = None,
        locale: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> List[Notification]:
        user = await self.user_repo.get_with_preferences(user_id)
        if not user or not user.is_active:
            logger.warning("notification_user_not_found_or_inactive", user_id=str(user_id))
            return []

        preferences = user.preferences
        user_locale = locale or (preferences.preferred_locale if preferences else None) or user.locale.value

        priority_enum = NotificationPriority(priority) if isinstance(priority, str) else priority
        event_type_enum = FinancialEventType(event_type) if isinstance(event_type, str) else event_type

        # Determine channels
        if channels:
            target_channels = [NotificationChannel(c) for c in channels]
        else:
            target_channels = [NotificationChannel(c) for c in CHANNEL_PRIORITY_MAP.get(priority_enum, [NotificationChannel.EMAIL])]

        notifications = []

        for channel in target_channels:
            notification = await self._build_single(
                user=user,
                event_type=event_type_enum,
                channel=channel,
                priority=priority_enum,
                event_data=event_data or {},
                locale=user_locale,
                idempotency_key=f"{idempotency_key}:{channel.value}" if idempotency_key else None,
            )
            if notification:
                notifications.append(notification)

        return notifications

    async def _build_single(
        self,
        user,
        event_type: FinancialEventType,
        channel: NotificationChannel,
        priority: NotificationPriority,
        event_data: Dict[str, Any],
        locale: str,
        idempotency_key: Optional[str],
    ) -> Optional[Notification]:
        preferences = user.preferences

        # Check channel preference
        channel_enabled = self._is_channel_enabled(channel, preferences)
        if not channel_enabled:
            return await self._skip(
                user, event_type, channel, priority, event_data, locale,
                idempotency_key, SkipReason.CHANNEL_DISABLED
            )

        # Check event opt-out
        if preferences:
            disabled_events = preferences.get_disabled_events()
            if event_type.value in disabled_events:
                return await self._skip(
                    user, event_type, channel, priority, event_data, locale,
                    idempotency_key, SkipReason.USER_OPT_OUT
                )

        # Get recipient
        recipient = self._get_recipient(user, channel)
        if not recipient:
            return await self._skip(
                user, event_type, channel, priority, event_data, locale,
                idempotency_key, SkipReason.INVALID_CONTACT
            )

        # Render template
        rendered = await self.template_service.render(event_type, channel, locale, event_data, user)
        if not rendered:
            logger.warning("template_not_found", event_type=event_type, channel=channel, locale=locale)
            return None

        notification_data = {
            "user_id": user.id,
            "event_type": event_type,
            "channel": channel,
            "status": NotificationStatus.PENDING,
            "priority": priority,
            "recipient": recipient,
            "subject": rendered.get("subject"),
            "body": rendered["body"],
            "template_id": rendered.get("template_id"),
            "locale": locale,
            "event_data": event_data,
            "max_retries": CHANNEL_MAX_RETRIES.get(channel, 3),
            "idempotency_key": idempotency_key,
        }
        return await self.notification_repo.create(notification_data)

    async def _skip(
        self, user, event_type, channel, priority, event_data, locale, idempotency_key, reason
    ) -> Optional[Notification]:
        recipient = self._get_recipient(user, channel) or user.email
        notification_data = {
            "user_id": user.id,
            "event_type": event_type,
            "channel": channel,
            "status": NotificationStatus.SKIPPED,
            "priority": priority,
            "recipient": recipient,
            "body": "",
            "locale": locale,
            "event_data": event_data,
            "max_retries": 0,
            "skip_reason": reason,
            "idempotency_key": idempotency_key,
        }
        return await self.notification_repo.create(notification_data)

    def _is_channel_enabled(self, channel: NotificationChannel, preferences) -> bool:
        if not preferences:
            return True
        channel_map = {
            NotificationChannel.SMS: preferences.sms_enabled,
            NotificationChannel.EMAIL: preferences.email_enabled,
            NotificationChannel.WHATSAPP: preferences.whatsapp_enabled,
            NotificationChannel.PUSH: preferences.push_enabled,
            NotificationChannel.IN_APP: preferences.in_app_enabled,
        }
        return channel_map.get(channel, True)

    def _get_recipient(self, user, channel: NotificationChannel) -> Optional[str]:
        if channel in (NotificationChannel.SMS, NotificationChannel.WHATSAPP):
            return user.phone
        if channel == NotificationChannel.EMAIL:
            return user.email
        if channel == NotificationChannel.PUSH:
            return user.firebase_token
        if channel == NotificationChannel.IN_APP:
            return str(user.id)
        return None
