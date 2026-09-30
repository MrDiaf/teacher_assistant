import uuid

from httpx import AsyncClient

from tests.helpers import create_calendar, create_course, create_event


async def test_course_crud_allows_duplicate_names(client: AsyncClient) -> None:
    created = await create_course(
        client,
        name="  Database Systems  ",
        course_code=" DAT101 ",
        term=" Autumn 2026 ",
    )
    duplicate = await create_course(client, course_code="DAT102")

    assert created["name"] == "Database Systems"
    assert created["course_code"] == "DAT101"
    assert created["term"] == "Autumn 2026"
    assert created["status"] == "active"
    assert created["source_type"] == "manual"

    listed = await client.get("/api/v1/courses")
    assert listed.status_code == 200
    assert {item["id"] for item in listed.json()} == {created["id"], duplicate["id"]}

    fetched = await client.get(f"/api/v1/courses/{created['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == created["id"]

    updated = await client.patch(
        f"/api/v1/courses/{created['id']}",
        json={
            "name": "Data Modelling",
            "course_code": None,
            "description": "Updated description",
            "term": "Spring 2027",
            "color": "#f4c75f",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Data Modelling"
    assert updated.json()["course_code"] is None
    assert updated.json()["description"] == "Updated description"
    assert updated.json()["term"] == "Spring 2027"
    assert updated.json()["color"] == "#f4c75f"


async def test_course_archive_restore_filter_and_delete(client: AsyncClient) -> None:
    course = await create_course(client)

    archived = await client.post(f"/api/v1/courses/{course['id']}/archive")
    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"

    archived_again = await client.post(f"/api/v1/courses/{course['id']}/archive")
    assert archived_again.status_code == 200
    assert archived_again.json()["status"] == "archived"

    active_list = await client.get("/api/v1/courses", params={"status": "active"})
    archived_list = await client.get("/api/v1/courses", params={"status": "archived"})
    assert active_list.status_code == 200
    assert active_list.json() == []
    assert [item["id"] for item in archived_list.json()] == [course["id"]]

    restored = await client.post(f"/api/v1/courses/{course['id']}/restore")
    assert restored.status_code == 200
    assert restored.json()["status"] == "active"

    deleted = await client.delete(f"/api/v1/courses/{course['id']}")
    assert deleted.status_code == 204
    missing = await client.get(f"/api/v1/courses/{course['id']}")
    assert missing.status_code == 404
    missing_body = missing.json()
    assert missing_body["code"] == "course_not_found"
    assert missing_body["message"] == "The requested course does not exist."
    assert missing_body["details"] == {"status_code": 404}
    assert uuid.UUID(missing_body["error_id"])
    assert uuid.UUID(missing_body["request_id"])


async def test_course_delete_does_not_delete_calendar_or_events(client: AsyncClient) -> None:
    course = await create_course(client)
    calendar = await create_calendar(client)
    event = await create_event(client, calendar["id"])

    deleted = await client.delete(f"/api/v1/courses/{course['id']}")
    assert deleted.status_code == 204

    calendar_response = await client.get(f"/api/v1/calendars/{calendar['id']}")
    event_response = await client.get(f"/api/v1/events/{event['id']}")
    assert calendar_response.status_code == 200
    assert event_response.status_code == 200


async def test_course_validation_rejects_invalid_or_protected_fields(
    client: AsyncClient,
) -> None:
    blank = await client.post("/api/v1/courses", json={"name": "   "})
    invalid_color = await client.post(
        "/api/v1/courses",
        json={"name": "Networks", "color": "green"},
    )
    protected_field = await client.post(
        "/api/v1/courses",
        json={"name": "Networks", "source_type": "lms_import"},
    )

    assert blank.status_code == 422
    assert invalid_color.status_code == 422
    assert protected_field.status_code == 422

    course = await create_course(client)
    empty_update = await client.patch(f"/api/v1/courses/{course['id']}", json={})
    null_name = await client.patch(
        f"/api/v1/courses/{course['id']}",
        json={"name": None},
    )
    status_bypass = await client.patch(
        f"/api/v1/courses/{course['id']}",
        json={"status": "archived"},
    )
    assert empty_update.status_code == 422
    assert null_name.status_code == 422
    assert status_bypass.status_code == 422


async def test_unknown_course_returns_clear_error(client: AsyncClient) -> None:
    course_id = uuid.uuid4()
    response = await client.post(f"/api/v1/courses/{course_id}/archive")

    assert response.status_code == 404
    body = response.json()
    assert body["code"] == "course_not_found"
    assert body["message"] == "The requested course does not exist."
    assert body["details"] == {"status_code": 404}
    assert uuid.UUID(body["error_id"])
    assert uuid.UUID(body["request_id"])
