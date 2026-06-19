from datetime import datetime
from typing import Optional

import httpx
import pytz

from app.core.config import settings
from app.core.constants import CRITICAL_EVENTS, DND_EXEMPT_EVENTS, FinancialEventType
from app.core.exceptions import DNDRegisteredError, QuietHoursError
from app.core.logging import get_logger
from app.redis.client import RedisCache, RedisKeys

logger = get_logger(__name__)

DND_CACHE_TTL = 86400  # 24h


class ComplianceService:
    def __init__(self, cache: Optional[RedisCache] = None):
        self.cache = cache

    async def check_quiet_hours(
        self,
        user_id: str,
        event_type: FinancialEventType,
        quiet_hours_start: int,
        quiet_hours_end: int,
        timezone_str: str = "Asia/Kolkata",
    ) -> None:
        if event_type in CRITICAL_EVENTS:
            return

        tz = pytz.timezone(timezone_str)
        local_hour = datetime.now(tz).hour

        in_quiet = False
        if quiet_hours_start > quiet_hours_end:
            # Wraps midnight e.g. 22:00 - 08:00
            in_quiet = local_hour >= quiet_hours_start or local_hour < quiet_hours_end
        else:
            in_quiet = quiet_hours_start <= local_hour < quiet_hours_end

        if in_quiet:
            raise QuietHoursError(
                f"Quiet hours active ({quiet_hours_start}:00 - {quiet_hours_end}:00 {timezone_str}) "
                f"for user {user_id}"
            )

    async def check_dnd(
        self,
        phone: str,
        event_type: FinancialEventType,
    ) -> None:
        if event_type in DND_EXEMPT_EVENTS:
            return

        if not settings.TRAI_DND_CHECK_ENABLED:
            return

        # Check cache first
        if self.cache:
            cached = await self.cache.get(RedisKeys.dnd_cache(phone))
            if cached is not None:
                if cached:
                    raise DNDRegisteredError(f"Phone {phone} is DND registered")
                return

        is_dnd = await self._query_dnd_registry(phone)

        if self.cache:
            await self.cache.set(RedisKeys.dnd_cache(phone), is_dnd, ttl=DND_CACHE_TTL)

        if is_dnd:
            raise DNDRegisteredError(f"Phone {phone} is registered on TRAI DND")

    async def _query_dnd_registry(self, phone: str) -> bool:
        if not settings.TRAI_DND_API_URL or not settings.TRAI_DND_API_KEY:
            return False
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{settings.TRAI_DND_API_URL}/check",
                    params={"phone": phone},
                    headers={"Authorization": f"Bearer {settings.TRAI_DND_API_KEY}"},
                )
                if response.status_code == 200:
                    data = response.json()
                    return data.get("is_dnd", False)
        except Exception as e:
            logger.warning("dnd_api_check_failed", phone=phone, error=str(e))
        return False
