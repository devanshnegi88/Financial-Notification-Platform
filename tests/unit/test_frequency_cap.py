from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.core.constants import NotificationChannel
from app.core.exceptions import FrequencyCapExceeded
from app.redis.frequency_cap import FrequencyCapService


@pytest.mark.asyncio
async def test_frequency_cap_not_exceeded():
    mock_redis = AsyncMock()
    mock_pipeline = AsyncMock()
    mock_pipeline.execute = AsyncMock(return_value=[0, None, 0, None, 0, None])
    mock_redis.pipeline.return_value = mock_pipeline

    service = FrequencyCapService(mock_redis)

    with patch("app.redis.frequency_cap.RedisKeys") as mock_keys:
        mock_keys.freq_cap_hourly.return_value = "freq:h:key"
        mock_keys.freq_cap_daily.return_value = "freq:d:key"
        mock_keys.freq_cap_weekly.return_value = "freq:w:key"

        mock_get_pipeline = AsyncMock()
        mock_get_pipeline.execute = AsyncMock(return_value=[b"2", b"5", b"10"])
        mock_redis.pipeline.return_value.__aenter__ = AsyncMock(return_value=mock_get_pipeline)
        mock_redis.pipeline.return_value.__aexit__ = AsyncMock(return_value=False)

        # patch get calls
        mock_redis.pipeline.return_value = MagicMock()
        mock_redis.pipeline.return_value.get = MagicMock()
        mock_redis.pipeline.return_value.execute = AsyncMock(return_value=[b"2", b"5", b"10"])
        mock_redis.pipeline.return_value.incr = MagicMock()
        mock_redis.pipeline.return_value.expire = MagicMock()

        # Should not raise — counts (2, 5, 10) are below defaults
        await service.check_and_increment(
            user_id=str(uuid4()),
            channel=NotificationChannel.SMS,
            cap_hourly=10,
            cap_daily=50,
            cap_weekly=200,
        )


@pytest.mark.asyncio
async def test_frequency_cap_hourly_exceeded():
    mock_redis = MagicMock()
    mock_pipeline = MagicMock()
    mock_pipeline.execute = AsyncMock(return_value=[b"11", b"20", b"50"])
    mock_pipeline.get = MagicMock()
    mock_redis.pipeline.return_value = mock_pipeline

    service = FrequencyCapService(mock_redis)

    with pytest.raises(FrequencyCapExceeded) as exc_info:
        await service.check_and_increment(
            user_id=str(uuid4()),
            channel=NotificationChannel.EMAIL,
            cap_hourly=10,
            cap_daily=50,
            cap_weekly=200,
        )
    assert "Hourly" in str(exc_info.value)


@pytest.mark.asyncio
async def test_frequency_cap_zero_means_unlimited():
    mock_redis = MagicMock()
    mock_pipeline = MagicMock()
    # Return very high counts — but cap is 0 (unlimited)
    mock_pipeline.execute = AsyncMock(return_value=[b"9999", b"9999", b"9999"])
    mock_pipeline.get = MagicMock()
    mock_pipeline.incr = MagicMock()
    mock_pipeline.expire = MagicMock()
    mock_redis.pipeline.return_value = mock_pipeline

    service = FrequencyCapService(mock_redis)

    # With cap=0 for all, should never raise
    await service.check_and_increment(
        user_id=str(uuid4()),
        channel=NotificationChannel.SMS,
        cap_hourly=0,
        cap_daily=0,
        cap_weekly=0,
    )
