from typing import Any

from httpx import AsyncClient


async def create_calendar(client: AsyncClient, **overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "name": "Personal",
        "description": "Ordinary local calendar",
        "color": "#29584c",
    }
    payload.update(overrides)
    response = await client.post("/api/v1/calendars", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


async def create_event(client: AsyncClient, calendar_id: str, **overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "calendar_id": calendar_id,
        "title": "Planning session",
        "description": "Prepare next week",
        "location": "Home office",
        "start_at": "2026-07-20T10:00:00+02:00",
        "end_at": "2026-07-20T11:00:00+02:00",
        "timezone": "Europe/Oslo",
    }
    payload.update(overrides)
    response = await client.post("/api/v1/events", json=payload)
    assert response.status_code == 201, response.text
    return response.json()
