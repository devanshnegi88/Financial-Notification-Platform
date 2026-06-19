from typing import List, Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import FinancialEventType, NotificationChannel
from app.models.template import NotificationTemplate
from app.repositories.base import BaseRepository


class TemplateRepository(BaseRepository[NotificationTemplate]):
    def __init__(self, session: AsyncSession):
        super().__init__(NotificationTemplate, session)

    async def get_by_event_channel_locale(
        self,
        event_type: FinancialEventType,
        channel: NotificationChannel,
        locale: str = "en",
    ) -> Optional[NotificationTemplate]:
        result = await self.session.execute(
            select(NotificationTemplate).where(
                and_(
                    NotificationTemplate.event_type == event_type,
                    NotificationTemplate.channel == channel,
                    NotificationTemplate.locale == locale,
                    NotificationTemplate.is_active == True,
                )
            )
        )
        template = result.scalar_one_or_none()
        # Fall back to English if locale template not found
        if template is None and locale != "en":
            result = await self.session.execute(
                select(NotificationTemplate).where(
                    and_(
                        NotificationTemplate.event_type == event_type,
                        NotificationTemplate.channel == channel,
                        NotificationTemplate.locale == "en",
                        NotificationTemplate.is_active == True,
                    )
                )
            )
            template = result.scalar_one_or_none()
        return template

    async def get_by_event_type(
        self, event_type: FinancialEventType
    ) -> List[NotificationTemplate]:
        result = await self.session.execute(
            select(NotificationTemplate).where(
                and_(
                    NotificationTemplate.event_type == event_type,
                    NotificationTemplate.is_active == True,
                )
            )
        )
        return list(result.scalars().all())
