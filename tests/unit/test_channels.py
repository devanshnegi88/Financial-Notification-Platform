from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.channels.in_app_channel import InAppChannel


@pytest.mark.asyncio
async def test_in_app_channel_always_succeeds():
    channel = InAppChannel()
    result = await channel.send(
        recipient="user-id-123",
        subject="Test Subject",
        body="Test Body",
    )
    assert result.success is True
    assert result.provider_message_id is not None
    assert result.latency_ms is not None


@pytest.mark.asyncio
async def test_in_app_channel_health():
    channel = InAppChannel()
    assert await channel.health_check() is True


@pytest.mark.asyncio
async def test_in_app_channel_name():
    channel = InAppChannel()
    assert channel.channel_name == "in_app"


@pytest.mark.asyncio
async def test_sms_channel_send_success():
    with patch("app.channels.sms_channel.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        mock_message = MagicMock()
        mock_message.sid = "SMtest123"
        mock_message.status = "queued"
        mock_client.messages.create.return_value = mock_message

        from app.channels.sms_channel import SMSChannel
        channel = SMSChannel()
        channel._client = mock_client

        result = await channel.send(
            recipient="+919876543210",
            subject=None,
            body="Test SMS body",
        )

        assert result.success is True
        assert result.provider_message_id == "SMtest123"
        assert result.latency_ms is not None


@pytest.mark.asyncio
async def test_sms_channel_send_failure():
    from twilio.base.exceptions import TwilioRestException

    with patch("app.channels.sms_channel.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.messages.create.side_effect = TwilioRestException(
            status=400, uri="/messages", msg="Invalid number", code=21211
        )

        from app.channels.sms_channel import SMSChannel
        channel = SMSChannel()
        channel._client = mock_client

        result = await channel.send(
            recipient="+1invalid",
            subject=None,
            body="Test",
        )

        assert result.success is False
        assert result.error_message is not None
        assert result.error_code == "21211"


@pytest.mark.asyncio
async def test_email_channel_send_success():
    with patch("app.channels.email_channel.SendGridAPIClient") as mock_sg_cls:
        mock_sg = MagicMock()
        mock_sg_cls.return_value = mock_sg

        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_response.headers = {"X-Message-Id": "msg-abc123"}
        mock_sg.send.return_value = mock_response

        from app.channels.email_channel import EmailChannel
        channel = EmailChannel()
        channel._client = mock_sg

        result = await channel.send(
            recipient="test@example.com",
            subject="Test Subject",
            body="Test body text",
            html_body="<p>Test body</p>",
        )

        assert result.success is True
        assert result.provider_message_id == "msg-abc123"
