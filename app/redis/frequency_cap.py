from typing import Optional

import redis.asyncio as aioredis

from app.core.config import settings
from app.core.constants import NotificationChannel
from app.core.exceptions import FrequencyCapExceeded
from app.redis.client import RedisKeys


class FrequencyCapService:
    def __init__(self, redis: aioredis.Redis):
        self.redis = redis

    async def check_and_increment(
        self,
        user_id: str,
        channel: NotificationChannel,
        cap_hourly: Optional[int] = None,
        cap_daily: Optional[int] = None,
        cap_weekly: Optional[int] = None,
    ) -> None:
        hourly_limit = cap_hourly or settings.FREQUENCY_CAP_HOURLY
        daily_limit = cap_daily or settings.FREQUENCY_CAP_DAILY
        weekly_limit = cap_weekly or settings.FREQUENCY_CAP_WEEKLY

        channel_val = channel.value if hasattr(channel, "value") else channel
        user_id_str = str(user_id)

        hourly_key = RedisKeys.freq_cap_hourly(user_id_str, channel_val)
        daily_key = RedisKeys.freq_cap_daily(user_id_str, channel_val)
        weekly_key = RedisKeys.freq_cap_weekly(user_id_str, channel_val)

        pipe = self.redis.pipeline()
        pipe.get(hourly_key)
        pipe.get(daily_key)
        pipe.get(weekly_key)
        results = await pipe.execute()

        hourly_count = int(results[0] or 0)
        daily_count = int(results[1] or 0)
        weekly_count = int(results[2] or 0)

        if hourly_limit > 0 and hourly_count >= hourly_limit:
            raise FrequencyCapExceeded(
                f"Hourly frequency cap exceeded: {hourly_count}/{hourly_limit} for user {user_id} on {channel_val}"
            )
        if daily_limit > 0 and daily_count >= daily_limit:
            raise FrequencyCapExceeded(
                f"Daily frequency cap exceeded: {daily_count}/{daily_limit} for user {user_id} on {channel_val}"
            )
        if weekly_limit > 0 and weekly_count >= weekly_limit:
            raise FrequencyCapExceeded(
                f"Weekly frequency cap exceeded: {weekly_count}/{weekly_limit} for user {user_id} on {channel_val}"
            )

        # Increment all counters
        pipe = self.redis.pipeline()
        pipe.incr(hourly_key)
        pipe.expire(hourly_key, 3600)
        pipe.incr(daily_key)
        pipe.expire(daily_key, 86400)
        pipe.incr(weekly_key)
        pipe.expire(weekly_key, 604800)
        await pipe.execute()

    async def get_counts(self, user_id: str, channel: NotificationChannel) -> dict:
        channel_val = channel.value if hasattr(channel, "value") else channel
        pipe = self.redis.pipeline()
        pipe.get(RedisKeys.freq_cap_hourly(user_id, channel_val))
        pipe.get(RedisKeys.freq_cap_daily(user_id, channel_val))
        pipe.get(RedisKeys.freq_cap_weekly(user_id, channel_val))
        results = await pipe.execute()
        return {
            "hourly": int(results[0] or 0),
            "daily": int(results[1] or 0),
            "weekly": int(results[2] or 0),
        }

    async def reset(self, user_id: str, channel: NotificationChannel) -> None:
        channel_val = channel.value if hasattr(channel, "value") else channel
        pipe = self.redis.pipeline()
        pipe.delete(RedisKeys.freq_cap_hourly(user_id, channel_val))
        pipe.delete(RedisKeys.freq_cap_daily(user_id, channel_val))
        pipe.delete(RedisKeys.freq_cap_weekly(user_id, channel_val))
        await pipe.execute()
