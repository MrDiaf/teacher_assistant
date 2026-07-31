import uuid

from httpx import AsyncClient

from tests.helpers import create_calendar


async def test_calendar_crud(client: AsyncClient) -> None:
    created = await create_calendar(client)

    listed = await client.get("/api/v1/calendars")
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [created["id"]]

    updated = await client.patch(
        f"/api/v1/calendars/{created['id']}",
        json={"name": "Private", "color": "#f4c75f"},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Private"
    assert updated.json()["color"] == "#f4c75f"

    fetched = await client.get(f"/api/v1/calendars/{created['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == created["id"]

    deleted = await client.delete(f"/api/v1/calendars/{created['id']}")
    assert deleted.status_code == 204

    missing = await client.get(f"/api/v1/calendars/{created['id']}")
    assert missing.status_code == 404
    assert missing.json()["code"] == "calendar_not_found"


async def test_unknown_calendar_returns_clear_error(client: AsyncClient) -> None:
    response = await client.get(f"/api/v1/calendars/{uuid.uuid4()}")
    assert response.status_code == 404
    body = response.json()
    assert body["code"] == "calendar_not_found"
    assert body["message"] == "The requested calendar does not exist."
    assert body["details"] == {"status_code": 404}
    assert uuid.UUID(body["error_id"])
    assert uuid.UUID(body["request_id"])


async def test_imported_calendar_defaults_to_read_only_and_cannot_unlock(
    client: AsyncClient,
) -> None:
    imported = await create_calendar(
        client,
        name="Imported timetable",
        source_type="ics_import",
        is_read_only=False,
    )
    assert imported["is_read_only"] is True

    unlock = await client.patch(f"/api/v1/calendars/{imported['id']}", json={"is_read_only": False})
    assert unlock.status_code == 403
    assert unlock.json()["code"] == "calendar_source_protected"

    deleted = await client.delete(f"/api/v1/calendars/{imported['id']}")
    assert deleted.status_code == 403


async def test_read_only_local_calendar_allows_visibility_and_manual_unlock_only(
    client: AsyncClient,
) -> None:
    calendar = await create_calendar(client, is_read_only=True)

    hidden = await client.patch(f"/api/v1/calendars/{calendar['id']}", json={"is_visible": False})
    assert hidden.status_code == 200
    assert hidden.json()["is_visible"] is False

    rename = await client.patch(
        f"/api/v1/calendars/{calendar['id']}", json={"name": "Bypass attempt"}
    )
    assert rename.status_code == 403
    assert rename.json()["code"] == "calendar_read_only"

    unlocked = await client.patch(
        f"/api/v1/calendars/{calendar['id']}", json={"is_read_only": False}
    )
    assert unlocked.status_code == 200
    assert unlocked.json()["is_read_only"] is False

    renamed = await client.patch(
        f"/api/v1/calendars/{calendar['id']}", json={"name": "Writable again"}
    )
    assert renamed.status_code == 200
