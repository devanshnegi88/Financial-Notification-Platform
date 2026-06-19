from datetime import date, timedelta

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_dashboard(client: AsyncClient, admin_headers: dict):
    today = date.today()
    from_date = today - timedelta(days=7)

    response = await client.get(
        "/api/v1/analytics/dashboard",
        params={"from_date": str(from_date), "to_date": str(today)},
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "total_notifications" in data
    assert "total_delivered" in data
    assert "total_failed" in data
    assert "delivery_rate" in data
    assert "by_channel" in data
    assert "by_event_type" in data
    assert "daily_trend" in data


@pytest.mark.asyncio
async def test_get_summary(client: AsyncClient, admin_headers: dict):
    today = date.today()
    from_date = today - timedelta(days=30)

    response = await client.get(
        "/api/v1/analytics/summary",
        params={"from_date": str(from_date), "to_date": str(today)},
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_get_channel_performance(client: AsyncClient, admin_headers: dict):
    today = date.today()
    from_date = today - timedelta(days=30)

    response = await client.get(
        "/api/v1/analytics/channel-performance",
        params={"from_date": str(from_date), "to_date": str(today)},
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_get_event_performance(client: AsyncClient, admin_headers: dict):
    today = date.today()
    from_date = today - timedelta(days=30)

    response = await client.get(
        "/api/v1/analytics/event-performance",
        params={"from_date": str(from_date), "to_date": str(today)},
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_get_skip_analysis(client: AsyncClient, admin_headers: dict):
    today = date.today()
    from_date = today - timedelta(days=30)

    response = await client.get(
        "/api/v1/analytics/skip-analysis",
        params={"from_date": str(from_date), "to_date": str(today)},
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_analytics_requires_analyst(client: AsyncClient, auth_headers: dict):
    """Regular users cannot access analytics."""
    response = await client.get(
        "/api/v1/analytics/dashboard",
        headers=auth_headers,
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_trigger_aggregation(client: AsyncClient, admin_headers: dict):
    yesterday = date.today() - timedelta(days=1)
    response = await client.post(
        "/api/v1/analytics/aggregate",
        params={"target_date": str(yesterday)},
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["date"] == str(yesterday)
