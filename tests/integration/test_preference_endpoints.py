import pytest
from httpx import AsyncClient

from app.models.user import User


@pytest.mark.asyncio
async def test_get_preferences(client: AsyncClient, auth_headers: dict, test_user: User):
    response = await client.get(
        f"/api/v1/preferences/{test_user.id}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == str(test_user.id)
    assert "sms_enabled" in data
    assert "email_enabled" in data
    assert "push_enabled" in data
    assert "whatsapp_enabled" in data
    assert "in_app_enabled" in data
    assert "quiet_hours_enabled" in data


@pytest.mark.asyncio
async def test_update_preferences(client: AsyncClient, auth_headers: dict, test_user: User):
    response = await client.put(
        f"/api/v1/preferences/{test_user.id}",
        json={
            "sms_enabled": False,
            "quiet_hours_start": 21,
            "quiet_hours_end": 7,
            "preferred_locale": "hi",
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["sms_enabled"] is False
    assert data["quiet_hours_start"] == 21
    assert data["quiet_hours_end"] == 7
    assert data["preferred_locale"] == "hi"


@pytest.mark.asyncio
async def test_update_preferences_forbidden_for_other_user(
    client: AsyncClient,
    auth_headers: dict,
    admin_user: User,
):
    """Regular user cannot update another user's preferences."""
    from uuid import uuid4
    other_user_id = admin_user.id

    response = await client.put(
        f"/api/v1/preferences/{other_user_id}",
        json={"sms_enabled": False},
        headers=auth_headers,
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_disable_event_types(client: AsyncClient, auth_headers: dict, test_user: User):
    response = await client.put(
        f"/api/v1/preferences/{test_user.id}",
        json={
            "disabled_event_types": ["offer.available", "offer.expiring"],
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "offer.available" in data["disabled_event_types"]
    assert "offer.expiring" in data["disabled_event_types"]


@pytest.mark.asyncio
async def test_reset_preferences(client: AsyncClient, auth_headers: dict, test_user: User):
    # First update
    await client.put(
        f"/api/v1/preferences/{test_user.id}",
        json={"sms_enabled": False, "preferred_locale": "hi"},
        headers=auth_headers,
    )

    # Then reset
    response = await client.post(
        f"/api/v1/preferences/{test_user.id}/reset",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    # Should be back to defaults
    assert data["sms_enabled"] is True
    assert data["preferred_locale"] == "en"


@pytest.mark.asyncio
async def test_update_frequency_caps(client: AsyncClient, auth_headers: dict, test_user: User):
    response = await client.put(
        f"/api/v1/preferences/{test_user.id}",
        json={
            "frequency_cap_hourly": 5,
            "frequency_cap_daily": 20,
            "frequency_cap_weekly": 100,
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["frequency_cap_hourly"] == 5
    assert data["frequency_cap_daily"] == 20
    assert data["frequency_cap_weekly"] == 100


@pytest.mark.asyncio
async def test_admin_can_update_any_user_preferences(
    client: AsyncClient,
    admin_headers: dict,
    test_user: User,
):
    response = await client.put(
        f"/api/v1/preferences/{test_user.id}",
        json={"email_enabled": False},
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["email_enabled"] is False
