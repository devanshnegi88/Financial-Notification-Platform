from fastapi import HTTPException, Request, status

from app.core.config import settings
from app.core.logging import get_logger
from app.redis.client import get_redis

logger = get_logger(__name__)


async def rate_limit_middleware(request: Request, call_next):
    if not settings.RATE_LIMIT_ENABLED:
        return await call_next(request)

    client_ip = request.client.host if request.client else "unknown"
    path = request.url.path

    if path in ("/health", "/metrics", "/docs", "/openapi.json", "/redoc"):
        return await call_next(request)

    try:
        redis = await get_redis()
        minute_key = f"rl:min:{client_ip}"
        hour_key = f"rl:hour:{client_ip}"

        pipe = redis.pipeline()
        pipe.incr(minute_key)
        pipe.expire(minute_key, 60)
        pipe.incr(hour_key)
        pipe.expire(hour_key, 3600)
        results = await pipe.execute()

        minute_count = results[0]
        hour_count = results[2]

        if minute_count > settings.RATE_LIMIT_REQUESTS_PER_MINUTE:
            logger.warning("rate_limit_exceeded_minute", ip=client_ip, count=minute_count)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded: too many requests per minute",
                headers={"Retry-After": "60"},
            )

        if hour_count > settings.RATE_LIMIT_REQUESTS_PER_HOUR:
            logger.warning("rate_limit_exceeded_hour", ip=client_ip, count=hour_count)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded: too many requests per hour",
                headers={"Retry-After": "3600"},
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("rate_limit_check_failed", error=str(e))

    return await call_next(request)
