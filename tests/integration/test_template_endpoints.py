from uuid import uuid4

import pytest
from httpx import AsyncClient


TEMPLATE_PAYLOAD = {
    "name": "Test Transaction Success SMS",
    "event_type": "transaction.success",
    "channel": "sms",
    "locale": "en",
    "body": "Dear {{ user_name }}, your transaction of ₹{{ amount }} was successful.",
    "variables": {"user_name": "string", "amount": "number"},
}


@pytest.mark.asyncio
async def test_create_template(client: AsyncClient, admin_headers: dict):
    payload = {**TEMPLATE_PAYLOAD, "name": f"Template {uuid4().hex[:6]}"}
    # Use a unique event/channel/locale combination
    payload["event_type"] = "investment.matured"
    payload["locale"] = "en"

    response = await client.post(
        "/api/v1/templates/",
        json=payload,
        headers=admin_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == payload["name"]
    assert data["event_type"] == "investment.matured"
    assert data["channel"] == "sms"
    assert data["is_active"] is True
    assert data["version"] == 1


@pytest.mark.asyncio
async def test_create_duplicate_template(client: AsyncClient, admin_headers: dict):
    payload = {
        **TEMPLATE_PAYLOAD,
        "event_type": "investment.dividend",
        "locale": "en",
    }
    await client.post("/api/v1/templates/", json=payload, headers=admin_headers)
    response = await client.post("/api/v1/templates/", json=payload, headers=admin_headers)
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_list_templates(client: AsyncClient, admin_headers: dict):
    response = await client.get("/api/v1/templates/", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_list_templates_filter_by_channel(client: AsyncClient, admin_headers: dict):
    response = await client.get(
        "/api/v1/templates/",
        params={"channel": "sms"},
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    for item in data["items"]:
        assert item["channel"] == "sms"


@pytest.mark.asyncio
async def test_get_template(client: AsyncClient, admin_headers: dict):
    payload = {
        **TEMPLATE_PAYLOAD,
        "event_type": "kyc.approved",
        "locale": "hi",
    }
    create_resp = await client.post("/api/v1/templates/", json=payload, headers=admin_headers)
    template_id = create_resp.json()["id"]

    response = await client.get(f"/api/v1/templates/{template_id}", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["id"] == template_id


@pytest.mark.asyncio
async def test_get_template_not_found(client: AsyncClient, admin_headers: dict):
    response = await client.get(f"/api/v1/templates/{uuid4()}", headers=admin_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_template(client: AsyncClient, admin_headers: dict):
    payload = {
        **TEMPLATE_PAYLOAD,
        "event_type": "kyc.rejected",
        "locale": "en",
    }
    create_resp = await client.post("/api/v1/templates/", json=payload, headers=admin_headers)
    template_id = create_resp.json()["id"]

    response = await client.put(
        f"/api/v1/templates/{template_id}",
        json={"body": "Updated body: {{ user_name }} your KYC was rejected."},
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "Updated body" in data["body"]
    assert data["version"] == 2


@pytest.mark.asyncio
async def test_delete_template(client: AsyncClient, admin_headers: dict):
    payload = {
        **TEMPLATE_PAYLOAD,
        "event_type": "system.maintenance",
        "locale": "en",
        "channel": "email",
    }
    create_resp = await client.post("/api/v1/templates/", json=payload, headers=admin_headers)
    template_id = create_resp.json()["id"]

    delete_resp = await client.delete(f"/api/v1/templates/{template_id}", headers=admin_headers)
    assert delete_resp.status_code == 200

    get_resp = await client.get(f"/api/v1/templates/{template_id}", headers=admin_headers)
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_render_template(client: AsyncClient, admin_headers: dict):
    payload = {
        "name": "Render Test Template",
        "event_type": "offer.available",
        "channel": "push",
        "locale": "en",
        "subject": "Offer for {{ user_name }}",
        "body": "Dear {{ user_name }}, you have an offer: {{ offer_description }}.",
    }
    create_resp = await client.post("/api/v1/templates/", json=payload, headers=admin_headers)
    template_id = create_resp.json()["id"]

    response = await client.post(
        "/api/v1/templates/render",
        json={
            "template_id": template_id,
            "variables": {
                "user_name": "Devansh",
                "offer_description": "20% cashback on first transaction",
            },
        },
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "Devansh" in data["body"]
    assert "20% cashback" in data["body"]
    assert "Devansh" in data["subject"]


@pytest.mark.asyncio
async def test_template_requires_admin(client: AsyncClient, auth_headers: dict):
    """Regular users cannot create templates."""
    response = await client.post(
        "/api/v1/templates/",
        json=TEMPLATE_PAYLOAD,
        headers=auth_headers,
    )
    assert response.status_code == 403
