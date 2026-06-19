from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.core.constants import FinancialEventType, NotificationChannel
from app.models.template import NotificationTemplate
from app.services.template_service import TemplateService


def _make_template(
    body="Dear {{ user_name }}, ₹{{ amount }} received.",
    subject="Credit of ₹{{ amount }}",
    html_body=None,
):
    tmpl = MagicMock(spec=NotificationTemplate)
    tmpl.id = uuid4()
    tmpl.body = body
    tmpl.subject = subject
    tmpl.html_body = html_body
    tmpl.is_active = True
    return tmpl


@pytest.mark.asyncio
async def test_render_basic_template():
    mock_session = AsyncMock()
    service = TemplateService(mock_session)

    service.repo = AsyncMock()
    service.repo.get_by_event_channel_locale = AsyncMock(
        return_value=_make_template()
    )

    user = MagicMock()
    user.full_name = "Devansh"
    user.email = "devansh@example.com"

    result = await service.render(
        event_type=FinancialEventType.ACCOUNT_CREDIT,
        channel=NotificationChannel.SMS,
        locale="en",
        context={"amount": "5000"},
        user=user,
    )

    assert result is not None
    assert "Devansh" in result["body"]
    assert "5000" in result["body"]
    assert "5000" in result["subject"]


@pytest.mark.asyncio
async def test_render_returns_none_when_template_missing():
    mock_session = AsyncMock()
    service = TemplateService(mock_session)

    service.repo = AsyncMock()
    service.repo.get_by_event_channel_locale = AsyncMock(return_value=None)

    result = await service.render(
        event_type=FinancialEventType.ACCOUNT_CREDIT,
        channel=NotificationChannel.WHATSAPP,
        locale="en",
        context={"amount": "1000"},
    )

    assert result is None


@pytest.mark.asyncio
async def test_render_with_html_body():
    mock_session = AsyncMock()
    service = TemplateService(mock_session)

    service.repo = AsyncMock()
    service.repo.get_by_event_channel_locale = AsyncMock(
        return_value=_make_template(
            html_body="<p>Dear {{ user_name }}, ₹{{ amount }} received.</p>"
        )
    )

    user = MagicMock()
    user.full_name = "Priya"
    user.email = "priya@example.com"

    result = await service.render(
        event_type=FinancialEventType.ACCOUNT_CREDIT,
        channel=NotificationChannel.EMAIL,
        locale="en",
        context={"amount": "2000"},
        user=user,
    )

    assert result is not None
    assert result["html_body"] is not None
    assert "Priya" in result["html_body"]
    assert "2000" in result["html_body"]


@pytest.mark.asyncio
async def test_render_handles_missing_variable_gracefully():
    mock_session = AsyncMock()
    service = TemplateService(mock_session)

    service.repo = AsyncMock()
    service.repo.get_by_event_channel_locale = AsyncMock(
        return_value=_make_template(body="Dear {{ user_name }}, amount {{ amount }}.")
    )

    user = MagicMock()
    user.full_name = "Test"
    user.email = "test@example.com"

    # `amount` is missing from context — StrictUndefined will cause render to fail gracefully
    result = await service.render(
        event_type=FinancialEventType.ACCOUNT_CREDIT,
        channel=NotificationChannel.SMS,
        locale="en",
        context={},  # Missing `amount`
        user=user,
    )

    # Should return None gracefully due to StrictUndefined
    assert result is None
