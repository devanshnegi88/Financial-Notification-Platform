import json
from typing import Any, Optional

import redis.asyncio as aioredis

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_redis_client: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            max_connections=50,
        )
    return _redis_client


async def close_redis() -> None:
    global _redis_client
    if _redis_client:
        await _redis_client.aclose()
        _redis_client = None


class RedisCache:
    def __init__(self, redis: aioredis.Redis):
        self.redis = redis

    async def get(self, key: str) -> Optional[Any]:
        value = await self.redis.get(key)
        if value is None:
            return None
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value

    async def set(self, key: str, value: Any, ttl: int = settings.REDIS_CACHE_TTL) -> None:
        serialized = json.dumps(value) if not isinstance(value, str) else value
        await self.redis.setex(key, ttl, serialized)

    async def delete(self, key: str) -> None:
        await self.redis.delete(key)

    async def exists(self, key: str) -> bool:
        return bool(await self.redis.exists(key))

    async def increment(self, key: str, ttl: Optional[int] = None) -> int:
        count = await self.redis.incr(key)
        if count == 1 and ttl:
            await self.redis.expire(key, ttl)
        return count

    async def get_many(self, keys: list[str]) -> list[Optional[Any]]:
        values = await self.redis.mget(keys)
        results = []
        for v in values:
            if v is None:
                results.append(None)
            else:
                try:
                    results.append(json.loads(v))
                except (json.JSONDecodeError, TypeError):
                    results.append(v)
        return results

    async def set_many(self, mapping: dict[str, Any], ttl: int = settings.REDIS_CACHE_TTL) -> None:
        pipe = self.redis.pipeline()
        for key, value in mapping.items():
            serialized = json.dumps(value) if not isinstance(value, str) else value
            pipe.setex(key, ttl, serialized)
        await pipe.execute()


class RedisKeys:
    @staticmethod
    def user_cache(user_id: str) -> str:
        return f"user:{user_id}"

    @staticmethod
    def user_preferences(user_id: str) -> str:
        return f"user:pref:{user_id}"

    @staticmethod
    def dnd_cache(phone: str) -> str:
        return f"dnd:{phone}"

    @staticmethod
    def freq_cap_hourly(user_id: str, channel: str) -> str:
        import arrow
        hour = arrow.utcnow().format("YYYY-MM-DD-HH")
        return f"freq:h:{user_id}:{channel}:{hour}"

    @staticmethod
    def freq_cap_daily(user_id: str, channel: str) -> str:
        import arrow
        day = arrow.utcnow().format("YYYY-MM-DD")
        return f"freq:d:{user_id}:{channel}:{day}"

    @staticmethod
    def freq_cap_weekly(user_id: str, channel: str) -> str:
        import arrow
        week = arrow.utcnow().format("YYYY-WW")
        return f"freq:w:{user_id}:{channel}:{week}"

    @staticmethod
    def rate_limit(identifier: str) -> str:
        return f"rl:{identifier}"

    @staticmethod
    def idempotency(key: str) -> str:
        return f"idem:{key}"

    @staticmethod
    def device_tokens(user_id: str) -> str:
        return f"device:{user_id}"
