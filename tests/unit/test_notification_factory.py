from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.core.constants import (
    FinancialEventType,
    NotificationChannel,
    NotificationPriority,
    NotificationStatus,
)
from app.models.user import User
from app.models.user_preference import UserPreference


def _make_user(
    email="test@example.com",
    phone="+919876543210",
    firebase_token="fcm-token-123",
    locale="en",
):
    user = MagicMock(spec=User)
    user.id = uuid4()
    user.email = email
    user.phone = phone
    user.firebase_token = firebase_token
    user.is_active = True
    user.full_name = "Test User"
    user.locale = MagicMock()
    user.locale.value = locale
    return user


def _make_preferences(**kwargs):
    pref = MagicMock(spec=UserPreference)
    pref.sms_enabled = kwargs.get("sms_enabled", True)
    pref.email_enabled = kwargs.get("email_enabled", True)
    pref.whatsapp_enabled = kwargs.get("whatsapp_enabled", False)
    pref.push_enabled = kwargs.get("push_enabled", True)
    pref.in_app_enabled = kwargs.get("in_app_enabled", True)
    pref.preferred_locale = kwargs.get("preferred_locale", "en")
    pref.get_disabled_events = MagicMock(return_value=kwargs.get("disabled_events", []))
    return pref


@pytest.mark.asyncio
async def test_factory_skips_channel_disabled():
    from app.services.notification_factory import NotificationFactory

    mock_session = AsyncMock()
    factory = NotificationFactory(mock_session)

    user = _make_user()
    user.preferences = _make_preferences(sms_enabled=False)

    factory.user_repo = AsyncMock()
    factory.user_repo.get_with_preferences = AsyncMock(return_value=user)

    factory.template_service = AsyncMock()
    factory.template_service.render = AsyncMock(return_value={"body": "test", "subject": "test"})

    factory.notification_repo = AsyncMock()
    created_notification = MagicMock()
    created_notification.status = NotificationStatus.SKIPPED
    factory.notification_repo.create = AsyncMock(return_value=created_notification)

    notifications = await factory.build_notifications(
        user_id=user.id,
        event_type=FinancialEventType.TRANSACTION_SUCCESS,
        priority=NotificationPriority.HIGH,
        channels=[NotificationChannel.SMS],
        event_data={"amount": "1000"},
    )

    assert len(notifications) == 1
    # Should have called create with SKIPPED status
    call_args = factory.notification_repo.create.call_args[0][0]
    from app.core.constants import SkipReason
    assert call_args["status"] == NotificationStatus.SKIPPED
    assert call_args["skip_reason"] == SkipReason.CHANNEL_DISABLED


@pytest.mark.asyncio
async def test_factory_skips_opted_out_event():
    from app.services.notification_factory import NotificationFactory

    mock_session = AsyncMock()
    factory = NotificationFactory(mock_session)

    user = _make_user()
    user.preferences = _make_preferences(
        disabled_events=[FinancialEventType.OFFER_AVAILABLE.value]
    )

    factory.user_repo = AsyncMock()
    factory.user_repo.get_with_preferences = AsyncMock(return_value=user)
    factory.template_service = AsyncMock()
    factory.notification_repo = AsyncMock()
    created = MagicMock()
    created.status = NotificationStatus.SKIPPED
    factory.notification_repo.create = AsyncMock(return_value=created)

    notifications = await factory.build_notifications(
        user_id=user.id,
        event_type=FinancialEventType.OFFER_AVAILABLE,
        priority=NotificationPriority.LOW,
        channels=[NotificationChannel.EMAIL],
        event_data={"offer_description": "10% off"},
    )

    assert len(notifications) == 1
    call_args = factory.notification_repo.create.call_args[0][0]
    from app.core.constants import SkipReason
    assert call_args["skip_reason"] == SkipReason.USER_OPT_OUT


@pytest.mark.asyncio
async def test_factory_skips_invalid_recipient():
    from app.services.notification_factory import NotificationFactory

    mock_session = AsyncMock()
    factory = NotificationFactory(mock_session)

    user = _make_user(phone=None)  # No phone — SMS should be skipped
    user.preferences = _make_preferences(sms_enabled=True)

    factory.user_repo = AsyncMock()
    factory.user_repo.get_with_preferences = AsyncMock(return_value=user)
    factory.template_service = AsyncMock()
    factory.notification_repo = AsyncMock()
    created = MagicMock()
    created.status = NotificationStatus.SKIPPED
    factory.notification_repo.create = AsyncMock(return_value=created)

    notifications = await factory.build_notifications(
        user_id=user.id,
        event_type=FinancialEventType.PAYMENT_DUE,
        priority=NotificationPriority.MEDIUM,
        channels=[NotificationChannel.SMS],
        event_data={"amount": "500"},
    )

    assert len(notifications) == 1
    call_args = factory.notification_repo.create.call_args[0][0]
    from app.core.constants import SkipReason
    assert call_args["skip_reason"] == SkipReason.INVALID_CONTACT


@pytest.mark.asyncio
async def test_factory_inactive_user_returns_empty():
    from app.services.notification_factory import NotificationFactory

    mock_session = AsyncMock()
    factory = NotificationFactory(mock_session)

    user = _make_user()
    user.is_active = False

    factory.user_repo = AsyncMock()
    factory.user_repo.get_with_preferences = AsyncMock(return_value=user)

    notifications = await factory.build_notifications(
        user_id=user.id,
        event_type=FinancialEventType.TRANSACTION_SUCCESS,
        priority=NotificationPriority.HIGH,
        channels=[NotificationChannel.SMS],
        event_data={},
    )

    assert notifications == []


@pytest.mark.asyncio
async def test_factory_user_not_found_returns_empty():
    from app.services.notification_factory import NotificationFactory

    mock_session = AsyncMock()
    factory = NotificationFactory(mock_session)

    factory.user_repo = AsyncMock()
    factory.user_repo.get_with_preferences = AsyncMock(return_value=None)

    notifications = await factory.build_notifications(
        user_id=uuid4(),
        event_type=FinancialEventType.TRANSACTION_SUCCESS,
        priority=NotificationPriority.HIGH,
        channels=[NotificationChannel.EMAIL],
        event_data={},
    )

    assert notifications == []
