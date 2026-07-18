import uuid

from httpx import AsyncClient

from tests.helpers import create_calendar, create_event


async def test_event_crud_move_and_date_filter(client: AsyncClient) -> None:
    source = await create_calendar(client, name="Source")
    target = await create_calendar(client, name="Target", color="#f4c75f")
    event = await create_event(client, source["id"])

    listed = await client.get(
        "/api/v1/events",
        params={
            "calendar_id": source["id"],
            "starts_before": "2026-07-20T12:00:00+02:00",
            "ends_after": "2026-07-20T09:00:00+02:00",
        },
    )
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [event["id"]]

    updated = await client.patch(
        f"/api/v1/events/{event['id']}",
        json={
            "calendar_id": target["id"],
            "title": "Moved planning session",
            "start_at": "2026-07-20T12:00:00+02:00",
            "end_at": "2026-07-20T13:30:00+02:00",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["calendar_id"] == target["id"]
    assert updated.json()["title"] == "Moved planning session"

    fetched = await client.get(f"/api/v1/events/{event['id']}")
    assert fetched.status_code == 200

    deleted = await client.delete(f"/api/v1/events/{event['id']}")
    assert deleted.status_code == 204

    missing = await client.get(f"/api/v1/events/{event['id']}")
    assert missing.status_code == 404
    assert missing.json()["code"] == "event_not_found"


async def test_event_rejects_invalid_calendar_and_time_range(client: AsyncClient) -> None:
    missing_calendar = await client.post(
        "/api/v1/events",
        json={
            "calendar_id": str(uuid.uuid4()),
            "title": "Impossible",
            "start_at": "2026-07-20T10:00:00+02:00",
            "end_at": "2026-07-20T11:00:00+02:00",
        },
    )
    assert missing_calendar.status_code == 404
    assert missing_calendar.json()["code"] == "calendar_not_found"

    calendar = await create_calendar(client)
    invalid_time = await client.post(
        "/api/v1/events",
        json={
            "calendar_id": calendar["id"],
            "title": "Backwards",
            "start_at": "2026-07-20T11:00:00+02:00",
            "end_at": "2026-07-20T10:00:00+02:00",
        },
    )
    assert invalid_time.status_code == 422


async def test_read_only_calendar_blocks_create_update_move_out_and_delete(
    client: AsyncClient,
) -> None:
    calendar = await create_calendar(client)
    writable_target = await create_calendar(client, name="Writable target")
    event = await create_event(client, calendar["id"])
    locked = await client.patch(f"/api/v1/calendars/{calendar['id']}", json={"is_read_only": True})
    assert locked.status_code == 200

    create = await client.post(
        "/api/v1/events",
        json={
            "calendar_id": calendar["id"],
            "title": "Blocked",
            "start_at": "2026-07-21T10:00:00+02:00",
            "end_at": "2026-07-21T11:00:00+02:00",
        },
    )
    update = await client.patch(f"/api/v1/events/{event['id']}", json={"title": "Blocked rename"})
    move_out = await client.patch(
        f"/api/v1/events/{event['id']}", json={"calendar_id": writable_target["id"]}
    )
    delete = await client.delete(f"/api/v1/events/{event['id']}")

    for response in (create, update, move_out, delete):
        assert response.status_code == 403
        assert response.json()["code"] == "calendar_read_only"


async def test_event_cannot_move_into_read_only_calendar(client: AsyncClient) -> None:
    source = await create_calendar(client, name="Writable source")
    target = await create_calendar(client, name="Protected target", is_read_only=True)
    event = await create_event(client, source["id"])

    response = await client.patch(
        f"/api/v1/events/{event['id']}", json={"calendar_id": target["id"]}
    )
    assert response.status_code == 403
    assert response.json()["code"] == "calendar_read_only"


async def test_recurrence_parent_must_exist_in_same_calendar(client: AsyncClient) -> None:
    first_calendar = await create_calendar(client, name="First")
    second_calendar = await create_calendar(client, name="Second")
    parent = await create_event(client, first_calendar["id"], recurrence_rule="FREQ=WEEKLY;COUNT=4")

    occurrence = await create_event(
        client,
        first_calendar["id"],
        title="One occurrence",
        recurrence_parent_id=parent["id"],
    )
    assert occurrence["recurrence_parent_id"] == parent["id"]

    invalid = await client.post(
        "/api/v1/events",
        json={
            "calendar_id": second_calendar["id"],
            "title": "Wrong calendar occurrence",
            "start_at": "2026-07-27T10:00:00+02:00",
            "end_at": "2026-07-27T11:00:00+02:00",
            "recurrence_parent_id": parent["id"],
        },
    )
    assert invalid.status_code == 400
    assert invalid.json()["code"] == "invalid_recurrence_parent"
