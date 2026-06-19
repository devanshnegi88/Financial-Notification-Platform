from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.core.constants import (
    FinancialEventType,
    NotificationChannel,
    NotificationPriority,
    NotificationStatus,
)
from app.models.notification import Notification
from app.models.user import User


@pytest.mark.asyncio
async def test_list_notifications_empty(client: AsyncClient, auth_headers: dict):
    response = await client.get("/api/v1/notifications/", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert isinstance(data["items"], list)


@pytest.mark.asyncio
async def test_get_unread_count(client: AsyncClient, auth_headers: dict):
    response = await client.get("/api/v1/notifications/unread-count", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "unread_count" in data
    assert isinstance(data["unread_count"], int)


@pytest.mark.asyncio
async def test_get_notification_not_found(client: AsyncClient, auth_headers: dict):
    response = await client.get(
        f"/api/v1/notifications/{uuid4()}", headers=auth_headers
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_trigger_event_requires_manager(client: AsyncClient, auth_headers: dict, test_user: User):
    """Regular users cannot trigger events."""
    response = await client.post(
        "/api/v1/notifications/events",
        json={
            "user_id": str(test_user.id),
            "event_type": FinancialEventType.TRANSACTION_SUCCESS,
            "priority": NotificationPriority.HIGH,
            "event_data": {"amount": "1000"},
        },
        headers=auth_headers,
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_trigger_event_as_admin(client: AsyncClient, admin_headers: dict, test_user: User):
    """Admin can trigger notification events."""
    with patch("app.api.v1.endpoints.notifications.get_producer") as mock_get_producer:
        mock_producer = AsyncMock()
        mock_producer.send_and_wait = AsyncMock()
        mock_get_producer.return_value = mock_producer

        response = await client.post(
            "/api/v1/notifications/events",
            json={
                "user_id": str(test_user.id),
                "event_type": "transaction.success",
                "priority": "high",
                "event_data": {"amount": "1000", "recipient": "John"},
            },
            headers=admin_headers,
        )
        assert response.status_code == 202
        data = response.json()
        assert "message" in data


@pytest.mark.asyncio
async def test_mark_notifications_read(
    client: AsyncClient,
    auth_headers: dict,
    test_user: User,
    db_session,
):
    # Create an in-app notification for this user
    notification = Notification(
        id=uuid4(),
        user_id=test_user.id,
        event_type=FinancialEventType.WELCOME,
        channel=NotificationChannel.IN_APP,
        status=NotificationStatus.DELIVERED,
        priority=NotificationPriority.LOW,
        recipient=str(test_user.id),
        body="Welcome!",
        locale="en",
        max_retries=1,
    )
    db_session.add(notification)
    await db_session.flush()

    response = await client.post(
        "/api/v1/notifications/mark-read",
        json={"notification_ids": [str(notification.id)]},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert "1" in response.json()["message"]


@pytest.mark.asyncio
async def test_list_notifications_with_filter(
    client: AsyncClient,
    auth_headers: dict,
    test_user: User,
    db_session,
):
    notification = Notification(
        id=uuid4(),
        user_id=test_user.id,
        event_type=FinancialEventType.ACCOUNT_CREDIT,
        channel=NotificationChannel.IN_APP,
        status=NotificationStatus.DELIVERED,
        priority=NotificationPriority.MEDIUM,
        recipient=str(test_user.id),
        body="Account credited",
        locale="en",
        max_retries=1,
    )
    db_session.add(notification)
    await db_session.flush()

    response = await client.get(
        "/api/v1/notifications/",
        params={"status": "delivered", "channel": "in_app"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    for item in data["items"]:
        assert item["status"] == "delivered"
        assert item["channel"] == "in_app"


@pytest.mark.asyncio
async def test_retry_notification_non_failed(
    client: AsyncClient,
    admin_headers: dict,
    test_user: User,
    db_session,
):
    """Can only retry failed/dead notifications."""
    notification = Notification(
        id=uuid4(),
        user_id=test_user.id,
        event_type=FinancialEventType.ACCOUNT_CREDIT,
        channel=NotificationChannel.SMS,
        status=NotificationStatus.DELIVERED,
        priority=NotificationPriority.MEDIUM,
        recipient="+919876543210",
        body="Test body",
        locale="en",
        max_retries=3,
    )
    db_session.add(notification)
    await db_session.flush()

    response = await client.post(
        f"/api/v1/notifications/{notification.id}/retry",
        headers=admin_headers,
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_cancel_pending_notification(
    client: AsyncClient,
    admin_headers: dict,
    test_user: User,
    db_session,
):
    notification = Notification(
        id=uuid4(),
        user_id=test_user.id,
        event_type=FinancialEventType.OFFER_AVAILABLE,
        channel=NotificationChannel.EMAIL,
        status=NotificationStatus.PENDING,
        priority=NotificationPriority.LOW,
        recipient="test@example.com",
        body="Special offer",
        locale="en",
        max_retries=3,
    )
    db_session.add(notification)
    await db_session.flush()

    response = await client.delete(
        f"/api/v1/notifications/{notification.id}",
        headers=admin_headers,
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_bulk_event_trigger(
    client: AsyncClient,
    admin_headers: dict,
    test_user: User,
):
    with patch("app.api.v1.endpoints.notifications.get_producer") as mock_get_producer:
        mock_producer = AsyncMock()
        mock_producer.send_and_wait = AsyncMock()
        mock_get_producer.return_value = mock_producer

        response = await client.post(
            "/api/v1/notifications/events/bulk",
            json={
                "user_ids": [str(test_user.id)],
                "event_type": "account.low_balance",
                "priority": "high",
                "event_data": {"balance": "100", "minimum_balance": "500"},
            },
            headers=admin_headers,
        )
        assert response.status_code == 202
        data = response.json()
        assert data["details"]["count"] == 1
