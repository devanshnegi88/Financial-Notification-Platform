"""
Frequency Capping Engine per ZeTheta spec Section A6.2.

Multi-dimensional caps:
- Global per-user daily:     max 12/day  (rolling 24h)
- Per-channel daily:         SMS=5, Push=8, Email=3
- Per-category hourly:       max 3/category/hour
- Cooldown between same-type: min 15 minutes

Override conditions:
- CRITICAL events bypass all caps
- Regulatory mandates bypass channel caps
"""

from typing import Optional

import redis.asyncio as aioredis

from app.core.exceptions import FrequencyCapExceeded
from app.core.logging import get_logger

logger = get_logger(__name__)

# ── Cap limits from spec ──────────────────────────────────────────────────────
GLOBAL_DAILY_CAP = 12
CHANNEL_DAILY_CAPS = {"sms": 5, "push": 8, "email": 3, "whatsapp": 5, "in_app": 50}
CATEGORY_HOURLY_CAP = 3
SAME_TYPE_COOLDOWN_SECONDS = 900   # 15 minutes
WEEKLY_DIGEST_THRESHOLD = 8        # if >8/day, suggest digest


def _global_daily_key(user_id: str) -> str:
    import arrow
    day = arrow.utcnow().format("YYYY-MM-DD")
    return f"cap:global:{user_id}:{day}"


def _channel_daily_key(user_id: str, channel: str) -> str:
    import arrow
    day = arrow.utcnow().format("YYYY-MM-DD")
    return f"cap:channel:{user_id}:{channel}:{day}"


def _category_hourly_key(user_id: str, category: str) -> str:
    import arrow
    hour = arrow.utcnow().format("YYYY-MM-DD-HH")
    return f"cap:category:{user_id}:{category}:{hour}"


def _cooldown_key(user_id: str, event_code: str) -> str:
    return f"cap:cooldown:{user_id}:{event_code}"


def _event_code_to_category(event_code: str) -> str:
    """Extract category prefix from event code (e.g. 'RISK-001' → 'RISK')."""
    return event_code.split("-")[0] if "-" in event_code else event_code


class SpecFrequencyCapService:
    def __init__(self, redis: aioredis.Redis):
        self.redis = redis

    async def check_and_increment(
        self,
        user_id: str,
        channel: str,
        event_code: str,
        is_critical: bool = False,
        is_regulatory_mandatory: bool = False,
    ) -> dict:
        """
        Check all frequency cap dimensions and increment counters.
        Returns cap metadata for audit logging.
        Raises FrequencyCapExceeded if any cap is hit.
        """
        if is_critical:
            logger.info(
                "frequency_cap_bypassed_critical",
                user_id=user_id,
                event_code=event_code,
            )
            # Still increment for tracking
            await self._increment_all(user_id, channel, event_code)
            return {"bypassed": True, "reason": "critical_event"}

        category = _event_code_to_category(event_code)

        pipe = self.redis.pipeline()
        pipe.get(_global_daily_key(user_id))
        pipe.get(_channel_daily_key(user_id, channel))
        pipe.get(_category_hourly_key(user_id, category))
        pipe.exists(_cooldown_key(user_id, event_code))
        results = await pipe.execute()

        global_count = int(results[0] or 0)
        channel_count = int(results[1] or 0)
        category_count = int(results[2] or 0)
        in_cooldown = bool(results[3])

        channel_limit = CHANNEL_DAILY_CAPS.get(channel, 10)

        # Check global daily cap
        if global_count >= GLOBAL_DAILY_CAP:
            raise FrequencyCapExceeded(
                f"Global daily cap hit: {global_count}/{GLOBAL_DAILY_CAP} for user {user_id}"
            )

        # Check per-channel daily cap (regulatory mandatory can bypass)
        if not is_regulatory_mandatory and channel_count >= channel_limit:
            raise FrequencyCapExceeded(
                f"Channel daily cap hit: {channel}={channel_count}/{channel_limit} for user {user_id}"
            )

        # Check per-category hourly cap
        if category_count >= CATEGORY_HOURLY_CAP:
            raise FrequencyCapExceeded(
                f"Category hourly cap hit: {category}={category_count}/{CATEGORY_HOURLY_CAP} for user {user_id}"
            )

        # Check same-type cooldown
        if in_cooldown:
            raise FrequencyCapExceeded(
                f"Cooldown active for {event_code} user {user_id} (15-min window)"
            )

        await self._increment_all(user_id, channel, event_code)

        return {
            "bypassed": False,
            "global_count": global_count + 1,
            "channel_count": channel_count + 1,
            "category_count": category_count + 1,
        }

    async def _increment_all(self, user_id: str, channel: str, event_code: str) -> None:
        category = _event_code_to_category(event_code)
        pipe = self.redis.pipeline()

        # Global daily
        gk = _global_daily_key(user_id)
        pipe.incr(gk)
        pipe.expire(gk, 86400)

        # Channel daily
        ck = _channel_daily_key(user_id, channel)
        pipe.incr(ck)
        pipe.expire(ck, 86400)

        # Category hourly
        catk = _category_hourly_key(user_id, category)
        pipe.incr(catk)
        pipe.expire(catk, 3600)

        # Cooldown
        cdk = _cooldown_key(user_id, event_code)
        pipe.set(cdk, "1", ex=SAME_TYPE_COOLDOWN_SECONDS)

        await pipe.execute()

    async def get_user_cap_status(self, user_id: str) -> dict:
        """Returns current cap usage for a user across all dimensions."""
        import arrow
        day = arrow.utcnow().format("YYYY-MM-DD")
        hour = arrow.utcnow().format("YYYY-MM-DD-HH")

        pipe = self.redis.pipeline()
        pipe.get(f"cap:global:{user_id}:{day}")
        for ch in CHANNEL_DAILY_CAPS:
            pipe.get(f"cap:channel:{user_id}:{ch}:{day}")
        pipe.execute()

        global_count_raw = await self.redis.get(f"cap:global:{user_id}:{day}")
        global_count = int(global_count_raw or 0)

        channel_counts = {}
        for ch, limit in CHANNEL_DAILY_CAPS.items():
            raw = await self.redis.get(f"cap:channel:{user_id}:{ch}:{day}")
            channel_counts[ch] = {"count": int(raw or 0), "limit": limit}

        suggest_digest = global_count >= WEEKLY_DIGEST_THRESHOLD

        return {
            "global_daily": {"count": global_count, "limit": GLOBAL_DAILY_CAP},
            "channels": channel_counts,
            "suggest_digest": suggest_digest,
        }

    async def reset_user_caps(self, user_id: str) -> None:
        """Admin: reset all caps for a user (e.g. testing)."""
        import arrow
        day = arrow.utcnow().format("YYYY-MM-DD")
        pattern = f"cap:*:{user_id}:*"
        keys = await self.redis.keys(pattern)
        if keys:
            await self.redis.delete(*keys)
        logger.info("frequency_caps_reset", user_id=user_id, keys_deleted=len(keys))
