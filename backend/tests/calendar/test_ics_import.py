from httpx import AsyncClient

from tests.helpers import create_calendar

VALID_ICS = b"""BEGIN:VCALENDAR\r
VERSION:2.0\r
PRODID:-//Teacher Assistant Tests//EN\r
X-WR-CALNAME:School Schedule\r
BEGIN:VEVENT\r
UID:lesson-1@example.test\r
DTSTART;TZID=Europe/Oslo:20260720T100000\r
DTEND;TZID=Europe/Oslo:20260720T113000\r
SUMMARY:Planning lesson\r
DESCRIPTION:Prepare chapter 4\\nBring notes\r
LOCATION:Room 2\r
STATUS:CONFIRMED\r
RRULE:FREQ=WEEKLY;COUNT=3\r
END:VEVENT\r
BEGIN:VEVENT\r
UID:holiday-1@example.test\r
DTSTART;VALUE=DATE:20260725\r
DTEND;VALUE=DATE:20260727\r
SUMMARY:School holiday\r
END:VEVENT\r
END:VCALENDAR\r
"""

PARTIAL_ICS = b"""BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:valid@example.test
DTSTART:20260720T100000Z
DTEND:20260720T110000Z
SUMMARY:Valid event
END:VEVENT
BEGIN:VEVENT
UID:unsupported@example.test
DTSTART:20260721T100000Z
DTEND:20260721T110000Z
SUMMARY:Unsupported recurrence
RRULE:FREQ=WEEKLY;BYDAY=MO
END:VEVENT
END:VCALENDAR
"""


async def preview(client: AsyncClient, content: bytes = VALID_ICS):
    return await client.post(
        "/api/v1/calendar-imports/ics/preview",
        params={"file_name": "schedule.ics"},
        content=content,
        headers={"Content-Type": "text/calendar"},
    )


async def import_ics(client: AsyncClient, content: bytes = VALID_ICS, **params):
    return await client.post(
        "/api/v1/calendar-imports/ics",
        params={"file_name": "schedule.ics", **params},
        content=content,
        headers={"Content-Type": "text/calendar"},
    )


async def test_preview_reports_timed_all_day_and_recurring_events(
    client: AsyncClient,
) -> None:
    response = await preview(client)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["suggested_calendar_name"] == "School Schedule"
    assert body["total_events"] == 2
    assert body["importable_events"] == 2
    assert body["skipped_events"] == 0
    assert body["events"][0] == {
        "index": 1,
        "uid": "lesson-1@example.test",
        "title": "Planning lesson",
        "start_at": "2026-07-20T10:00:00+02:00",
        "end_at": "2026-07-20T11:30:00+02:00",
        "all_day": False,
        "timezone": "Europe/Oslo",
        "status": "confirmed",
        "recurrence_rule": "FREQ=WEEKLY;COUNT=3",
        "is_importable": True,
        "issues": [],
    }
    assert body["events"][1]["all_day"] is True


async def test_import_creates_protected_calendar_and_preserves_external_uids(
    client: AsyncClient,
) -> None:
    response = await import_ics(
        client,
        calendar_name="Imported school",
        calendar_color="#5b7fa3",
    )

    assert response.status_code == 200, response.text
    body = response.json()
    calendar = body["calendar"]
    assert calendar["name"] == "Imported school"
    assert calendar["source_type"] == "ics_import"
    assert calendar["is_read_only"] is True
    assert body["imported_count"] == 2
    assert body["duplicate_count"] == 0
    assert {event["external_uid"] for event in body["imported_events"]} == {
        "lesson-1@example.test",
        "holiday-1@example.test",
    }

    event_id = body["imported_events"][0]["id"]
    update = await client.patch(f"/api/v1/events/{event_id}", json={"title": "Protection bypass"})
    delete = await client.delete(f"/api/v1/events/{event_id}")
    for blocked in (update, delete):
        assert blocked.status_code == 403
        assert blocked.json()["code"] == "calendar_read_only"


async def test_import_into_writable_calendar_skips_duplicate_uids(
    client: AsyncClient,
) -> None:
    calendar = await create_calendar(client, name="Copied imports")

    first = await import_ics(client, destination_calendar_id=calendar["id"])
    second = await import_ics(client, destination_calendar_id=calendar["id"])

    assert first.status_code == 200, first.text
    assert first.json()["imported_count"] == 2
    assert first.json()["calendar"]["is_read_only"] is False
    assert first.json()["calendar"]["source_type"] == "local"
    assert second.status_code == 200, second.text
    assert second.json()["imported_count"] == 0
    assert second.json()["duplicate_count"] == 2
    events = await client.get("/api/v1/events", params={"calendar_id": calendar["id"]})
    assert len(events.json()) == 2


async def test_preview_and_import_report_unsupported_events_without_partial_failure(
    client: AsyncClient,
) -> None:
    preview_response = await preview(client, PARTIAL_ICS)
    assert preview_response.status_code == 200
    preview_body = preview_response.json()
    assert preview_body["importable_events"] == 1
    assert preview_body["skipped_events"] == 1
    assert preview_body["events"][1]["is_importable"] is False
    assert "simple daily, weekly, or monthly" in preview_body["events"][1]["issues"][0]["message"]

    imported = await import_ics(client, PARTIAL_ICS)
    assert imported.status_code == 200, imported.text
    assert imported.json()["imported_count"] == 1
    assert imported.json()["skipped_count"] == 1
    assert imported.json()["errors"][0]["uid"] == "unsupported@example.test"


async def test_malformed_or_empty_import_does_not_create_calendar(
    client: AsyncClient,
) -> None:
    malformed = await preview(client, b"this is not a calendar")
    assert malformed.status_code == 400
    assert malformed.json()["code"] == "invalid_ics"

    no_valid_events = await import_ics(
        client,
        b"""BEGIN:VCALENDAR
BEGIN:VEVENT
UID:broken@example.test
SUMMARY:No dates
END:VEVENT
END:VCALENDAR
""",
    )
    assert no_valid_events.status_code == 400
    assert no_valid_events.json()["code"] == "invalid_ics"
    assert (await client.get("/api/v1/calendars")).json() == []


async def test_read_only_destination_rejects_import(client: AsyncClient) -> None:
    calendar = await create_calendar(client, name="Protected", is_read_only=True)
    response = await import_ics(client, destination_calendar_id=calendar["id"])
    assert response.status_code == 403
    assert response.json()["code"] == "calendar_read_only"


async def test_duplicate_uid_inside_one_file_is_reported(client: AsyncClient) -> None:
    duplicate_file = VALID_ICS.replace(b"holiday-1@example.test", b"lesson-1@example.test")
    response = await preview(client, duplicate_file)
    assert response.status_code == 200
    assert response.json()["importable_events"] == 1
    assert response.json()["events"][1]["issues"][0]["severity"] == "error"


async def test_moving_imported_copy_cannot_create_duplicate_uid(
    client: AsyncClient,
) -> None:
    first_calendar = await create_calendar(client, name="First")
    second_calendar = await create_calendar(client, name="Second")
    first_import = await import_ics(client, destination_calendar_id=first_calendar["id"])
    await import_ics(client, destination_calendar_id=second_calendar["id"])

    response = await client.patch(
        f"/api/v1/events/{first_import.json()['imported_events'][0]['id']}",
        json={"calendar_id": second_calendar["id"]},
    )
    assert response.status_code == 409
    assert response.json()["code"] == "duplicate_external_uid"
