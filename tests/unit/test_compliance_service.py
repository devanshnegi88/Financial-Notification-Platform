from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.core.constants import FinancialEventType
from app.core.exceptions import DNDRegisteredError, QuietHoursError
from app.services.compliance_service import ComplianceService


@pytest.mark.asyncio
async def test_quiet_hours_active():
    service = ComplianceService()
    with patch("app.services.compliance_service.datetime") as mock_dt:
        mock_now = MagicMock()
        mock_now.hour = 23  # 11 PM — within quiet hours 22:00–08:00
        mock_dt.now.return_value = mock_now

        with pytest.raises(QuietHoursError):
            await service.check_quiet_hours(
                user_id=str(uuid4()),
                event_type=FinancialEventType.PAYMENT_DUE,
                quiet_hours_start=22,
                quiet_hours_end=8,
                timezone_str="Asia/Kolkata",
            )


@pytest.mark.asyncio
async def test_quiet_hours_inactive():
    service = ComplianceService()
    with patch("app.services.compliance_service.datetime") as mock_dt:
        mock_now = MagicMock()
        mock_now.hour = 14  # 2 PM — outside quiet hours
        mock_dt.now.return_value = mock_now

        # Should not raise
        await service.check_quiet_hours(
            user_id=str(uuid4()),
            event_type=FinancialEventType.PAYMENT_DUE,
            quiet_hours_start=22,
            quiet_hours_end=8,
            timezone_str="Asia/Kolkata",
        )


@pytest.mark.asyncio
async def test_critical_event_bypasses_quiet_hours():
    service = ComplianceService()
    # SUSPICIOUS_ACTIVITY is in CRITICAL_EVENTS — should bypass quiet hours
    with patch("app.services.compliance_service.datetime") as mock_dt:
        mock_now = MagicMock()
        mock_now.hour = 23
        mock_dt.now.return_value = mock_now

        # Should NOT raise even during quiet hours
        await service.check_quiet_hours(
            user_id=str(uuid4()),
            event_type=FinancialEventType.SUSPICIOUS_ACTIVITY,
            quiet_hours_start=22,
            quiet_hours_end=8,
            timezone_str="Asia/Kolkata",
        )


@pytest.mark.asyncio
async def test_dnd_exempt_event():
    service = ComplianceService()
    # OTP is DND exempt — should not raise
    await service.check_dnd(
        phone="+919876543210",
        event_type=FinancialEventType.OTP_GENERATED,
    )


@pytest.mark.asyncio
async def test_dnd_disabled_globally():
    from unittest.mock import patch
    service = ComplianceService()
    with patch("app.services.compliance_service.settings") as mock_settings:
        mock_settings.TRAI_DND_CHECK_ENABLED = False
        # Should not raise even for non-exempt events
        await service.check_dnd(
            phone="+919876543210",
            event_type=FinancialEventType.PAYMENT_DUE,
        )
