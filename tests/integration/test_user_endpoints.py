from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.models.user import User


@pytest.mark.asyncio
async def test_list_users_requires_manager(client: AsyncClient, auth_headers: dict):
    """Regular users cannot list all users."""
    response = await client.get("/api/v1/users/", headers=auth_headers)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_list_users_as_admin(client: AsyncClient, admin_headers: dict):
    response = await client.get("/api/v1/users/", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_get_own_user(client: AsyncClient, auth_headers: dict, test_user: User):
    response = await client.get(f"/api/v1/users/{test_user.id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(test_user.id)
    assert data["email"] == test_user.email


@pytest.mark.asyncio
async def test_get_other_user_forbidden(
    client: AsyncClient, auth_headers: dict, admin_user: User
):
    """Regular user cannot fetch another user's profile."""
    response = await client.get(f"/api/v1/users/{admin_user.id}", headers=auth_headers)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_get_any_user(
    client: AsyncClient, admin_headers: dict, test_user: User
):
    response = await client.get(f"/api/v1/users/{test_user.id}", headers=admin_headers)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_update_own_profile(client: AsyncClient, auth_headers: dict, test_user: User):
    response = await client.put(
        f"/api/v1/users/{test_user.id}",
        json={"full_name": "Updated Name", "timezone": "Asia/Mumbai"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == "Updated Name"
    assert data["timezone"] == "Asia/Mumbai"


@pytest.mark.asyncio
async def test_update_other_user_forbidden(
    client: AsyncClient, auth_headers: dict, admin_user: User
):
    response = await client.put(
        f"/api/v1/users/{admin_user.id}",
        json={"full_name": "Hacked Name"},
        headers=auth_headers,
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_delete_user_requires_admin(
    client: AsyncClient, auth_headers: dict, test_user: User
):
    response = await client.delete(f"/api/v1/users/{test_user.id}", headers=auth_headers)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_delete_user_as_admin(
    client: AsyncClient, admin_headers: dict, db_session
):
    from app.core.security import get_password_hash
    from app.models.user_preference import UserPreference

    # Create a throwaway user to delete
    user = User(
        id=uuid4(),
        email=f"todelete_{uuid4().hex[:8]}@example.com",
        hashed_password=get_password_hash("DeleteMe123"),
        full_name="To Delete",
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    pref = UserPreference(user_id=user.id)
    db_session.add(pref)
    await db_session.flush()

    response = await client.delete(f"/api/v1/users/{user.id}", headers=admin_headers)
    assert response.status_code == 200

    get_resp = await client.get(f"/api/v1/users/{user.id}", headers=admin_headers)
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_list_users_filter_by_active(client: AsyncClient, admin_headers: dict):
    response = await client.get(
        "/api/v1/users/",
        params={"is_active": True},
        headers=admin_headers,
    )
    assert response.status_code == 200
    for user in response.json()["items"]:
        assert user["is_active"] is True


@pytest.mark.asyncio
async def test_get_nonexistent_user(client: AsyncClient, admin_headers: dict):
    response = await client.get(f"/api/v1/users/{uuid4()}", headers=admin_headers)
    assert response.status_code == 404
