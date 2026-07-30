import uuid

from httpx import AsyncClient

from tests.helpers import create_calendar, create_course, create_event


async def link_calendar(
    client: AsyncClient,
    course_id: str,
    calendar_id: str,
) -> dict[str, object]:
    response = await client.post(
        f"/api/v1/courses/{course_id}/calendars",
        json={"calendar_id": calendar_id},
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_course_links_several_calendars_without_duplicate_events(
    client: AsyncClient,
) -> None:
    course = await create_course(client)
    lectures = await create_calendar(client, name="Lectures")
    seminars = await create_calendar(client, name="Seminars", color="#f4c75f")
    lecture_event = await create_event(client, lectures["id"], title="Database lecture")
    seminar_event = await create_event(
        client,
        seminars["id"],
        title="Database seminar",
        start_at="2026-07-21T10:00:00+02:00",
        end_at="2026-07-21T11:00:00+02:00",
    )

    await link_calendar(client, course["id"], lectures["id"])
    await link_calendar(client, course["id"], seminars["id"])
    await link_calendar(client, course["id"], lectures["id"])

    linked = await client.get(f"/api/v1/courses/{course['id']}/calendars")
    assert linked.status_code == 200
    assert [calendar["id"] for calendar in linked.json()] == [
        lectures["id"],
        seminars["id"],
    ]

    events = await client.get(
        f"/api/v1/courses/{course['id']}/events",
        params={
            "starts_before": "2026-07-22T00:00:00+02:00",
            "ends_after": "2026-07-20T00:00:00+02:00",
        },
    )
    assert events.status_code == 200
    assert [event["id"] for event in events.json()] == [
        lecture_event["id"],
        seminar_event["id"],
    ]
    assert len({event["id"] for event in events.json()}) == 2

    filtered = await client.get(
        f"/api/v1/courses/{course['id']}/events",
        params={
            "calendar_id": seminars["id"],
            "search": "seminar",
        },
    )
    assert filtered.status_code == 200
    assert [event["id"] for event in filtered.json()] == [seminar_event["id"]]

    fetched_course = await client.get(f"/api/v1/courses/{course['id']}")
    assert fetched_course.status_code == 200
    assert fetched_course.json()["calendar_count"] == 2


async def test_course_calendar_routes_validate_course_calendar_and_link_scope(
    client: AsyncClient,
) -> None:
    course = await create_course(client)
    calendar = await create_calendar(client)
    missing_course_id = uuid.uuid4()
    missing_calendar_id = uuid.uuid4()

    missing_course = await client.post(
        f"/api/v1/courses/{missing_course_id}/calendars",
        json={"calendar_id": calendar["id"]},
    )
    missing_calendar = await client.post(
        f"/api/v1/courses/{course['id']}/calendars",
        json={"calendar_id": str(missing_calendar_id)},
    )
    unlinked_filter = await client.get(
        f"/api/v1/courses/{course['id']}/events",
        params={"calendar_id": calendar["id"]},
    )

    assert missing_course.status_code == 404
    assert missing_course.json()["code"] == "course_not_found"
    assert missing_calendar.status_code == 404
    assert missing_calendar.json()["code"] == "calendar_not_found"
    assert unlinked_filter.status_code == 404
    assert unlinked_filter.json() == {
        "code": "course_calendar_not_linked",
        "message": "The requested calendar is not linked to this course.",
    }


async def test_unlink_and_course_delete_preserve_calendar_and_event_data(
    client: AsyncClient,
) -> None:
    course = await create_course(client)
    calendar = await create_calendar(client)
    event = await create_event(client, calendar["id"])
    await link_calendar(client, course["id"], calendar["id"])

    unlinked = await client.delete(
        f"/api/v1/courses/{course['id']}/calendars/{calendar['id']}"
    )
    assert unlinked.status_code == 204
    assert (await client.get(f"/api/v1/courses/{course['id']}/calendars")).json() == []
    assert (await client.get(f"/api/v1/calendars/{calendar['id']}")).status_code == 200
    assert (await client.get(f"/api/v1/events/{event['id']}")).status_code == 200

    await link_calendar(client, course["id"], calendar["id"])
    deleted_course = await client.delete(f"/api/v1/courses/{course['id']}")
    assert deleted_course.status_code == 204
    assert (await client.get(f"/api/v1/calendars/{calendar['id']}")).status_code == 200
    assert (await client.get(f"/api/v1/events/{event['id']}")).status_code == 200


async def test_linked_read_only_calendar_remains_visible_and_protected(
    client: AsyncClient,
) -> None:
    course = await create_course(client)
    calendar = await create_calendar(client)
    event = await create_event(client, calendar["id"], title="Protected lecture")
    protected = await client.patch(
        f"/api/v1/calendars/{calendar['id']}",
        json={"is_read_only": True},
    )
    assert protected.status_code == 200
    await link_calendar(client, course["id"], calendar["id"])

    course_events = await client.get(f"/api/v1/courses/{course['id']}/events")
    assert course_events.status_code == 200
    assert [item["id"] for item in course_events.json()] == [event["id"]]

    create = await client.post(
        "/api/v1/events",
        json={
            "calendar_id": calendar["id"],
            "title": "Blocked",
            "start_at": "2026-07-22T10:00:00+02:00",
            "end_at": "2026-07-22T11:00:00+02:00",
        },
    )
    update = await client.patch(
        f"/api/v1/events/{event['id']}",
        json={"title": "Blocked rename"},
    )
    delete = await client.delete(f"/api/v1/events/{event['id']}")
    for response in (create, update, delete):
        assert response.status_code == 403
        assert response.json()["code"] == "calendar_read_only"


async def test_deleting_calendar_removes_only_its_course_link(
    client: AsyncClient,
) -> None:
    course = await create_course(client)
    calendar = await create_calendar(client)
    await link_calendar(client, course["id"], calendar["id"])

    deleted = await client.delete(f"/api/v1/calendars/{calendar['id']}")
    assert deleted.status_code == 204

    linked = await client.get(f"/api/v1/courses/{course['id']}/calendars")
    course_response = await client.get(f"/api/v1/courses/{course['id']}")
    assert linked.status_code == 200
    assert linked.json() == []
    assert course_response.status_code == 200
    assert course_response.json()["calendar_count"] == 0
