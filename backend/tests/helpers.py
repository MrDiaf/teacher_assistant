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


async def create_course(client: AsyncClient, **overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "name": "Database Systems",
        "course_code": "DAT101",
        "description": "Relational data and query design",
        "term": "Autumn 2026",
        "color": "#29584c",
    }
    payload.update(overrides)
    response = await client.post("/api/v1/courses", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


async def upload_course_source(
    client: AsyncClient,
    course_id: str,
    *,
    file_name: str,
    content: bytes,
    source_type: str = "literature",
    display_name: str | None = None,
) -> dict[str, Any]:
    params = {
        "source_type": source_type,
        "file_name": file_name,
    }
    if display_name is not None:
        params["display_name"] = display_name
    response = await client.post(
        f"/api/v1/courses/{course_id}/sources",
        params=params,
        content=content,
        headers={"Content-Type": "application/octet-stream"},
    )
    assert response.status_code == 201, response.text
    return response.json()


async def create_note(
    client: AsyncClient,
    course_id: str,
    **overrides: Any,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "title": "Lecture notes",
        "body": "Important course ideas.",
        "slide_references": [],
    }
    payload.update(overrides)
    response = await client.post(f"/api/v1/courses/{course_id}/notes", json=payload)
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
