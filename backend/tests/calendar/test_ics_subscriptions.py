from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.calendar.errors import IcsSubscriptionFetchError
from app.calendar.models import Calendar
from app.calendar.subscription_scheduler import refresh_due_subscriptions
from tests.calendar.test_ics_import import VALID_ICS

REFRESHED_ICS = b"""BEGIN:VCALENDAR
VERSION:2.0
X-WR-CALNAME:School Schedule
BEGIN:VEVENT
UID:lesson-1@example.test
DTSTART;TZID=Europe/Oslo:20260720T120000
DTEND;TZID=Europe/Oslo:20260720T133000
SUMMARY:Updated planning lesson
END:VEVENT
BEGIN:VEVENT
UID:new-lesson@example.test
DTSTART:20260722T080000Z
DTEND:20260722T090000Z
SUMMARY:New lesson
END:VEVENT
END:VCALENDAR
"""


def install_fetch(monkeypatch, content: bytes) -> None:
    async def fake_fetch(_url: str) -> bytes:
        return content

    monkeypatch.setattr("app.calendar.subscription_service.fetch_ics", fake_fetch)


async def create_subscription(client: AsyncClient, url: str = "https://example.test/private.ics"):
    return await client.post(
        "/api/v1/calendar-subscriptions/ics",
        json={
            "url": url,
            "calendar_name": "Subscribed school",
            "calendar_color": "#5b7fa3",
        },
    )


async def test_subscription_preview_and_create_keep_url_private_and_calendar_protected(
    client: AsyncClient,
    monkeypatch,
) -> None:
    private_url = "https://example.test/calendar.ics?private-token=secret"
    install_fetch(monkeypatch, VALID_ICS)

    preview = await client.post(
        "/api/v1/calendar-subscriptions/ics/preview",
        json={"url": private_url},
    )
    created = await create_subscription(client, private_url)

    assert preview.status_code == 200, preview.text
    assert preview.json()["importable_events"] == 2
    assert created.status_code == 200, created.text
    body = created.json()
    assert body["imported_count"] == 2
    assert body["calendar"]["is_subscribed"] is True
    assert body["calendar"]["is_read_only"] is True
    assert body["calendar"]["subscription_last_synced_at"] is not None
    assert body["calendar"]["subscription_next_sync_at"] is not None
    assert "private-token" not in created.text
    assert "secret" not in created.text

    event_id = body["imported_events"][0]["id"]
    blocked = await client.patch(f"/api/v1/events/{event_id}", json={"title": "Bypass"})
    assert blocked.status_code == 403
    assert blocked.json()["code"] == "calendar_read_only"


async def test_manual_subscription_sync_reconciles_events_by_uid(
    client: AsyncClient,
    monkeypatch,
) -> None:
    install_fetch(monkeypatch, VALID_ICS)
    created = await create_subscription(client)
    calendar_id = created.json()["calendar"]["id"]
    install_fetch(monkeypatch, REFRESHED_ICS)

    synced = await client.post(f"/api/v1/calendar-subscriptions/ics/{calendar_id}/sync")

    assert synced.status_code == 200, synced.text
    assert {
        key: synced.json()[key]
        for key in ("created_count", "updated_count", "deleted_count", "skipped_count")
    } == {
        "created_count": 1,
        "updated_count": 1,
        "deleted_count": 1,
        "skipped_count": 0,
    }
    events = (await client.get("/api/v1/events", params={"calendar_id": calendar_id})).json()
    assert {event["external_uid"] for event in events} == {
        "lesson-1@example.test",
        "new-lesson@example.test",
    }
    assert (
        next(event for event in events if event["external_uid"] == "lesson-1@example.test")["title"]
        == "Updated planning lesson"
    )

    blocked = await client.delete(f"/api/v1/events/{events[0]['id']}")
    assert blocked.status_code == 403


async def test_failed_refresh_keeps_events_and_records_safe_status(
    client: AsyncClient,
    monkeypatch,
) -> None:
    install_fetch(monkeypatch, VALID_ICS)
    created = await create_subscription(client)
    calendar_id = created.json()["calendar"]["id"]

    async def failed_fetch(_url: str) -> bytes:
        raise IcsSubscriptionFetchError("The source is temporarily unavailable.")

    monkeypatch.setattr("app.calendar.subscription_service.fetch_ics", failed_fetch)
    failed = await client.post(f"/api/v1/calendar-subscriptions/ics/{calendar_id}/sync")

    assert failed.status_code == 502
    calendars = (await client.get("/api/v1/calendars")).json()
    subscribed = next(calendar for calendar in calendars if calendar["id"] == calendar_id)
    assert subscribed["subscription_error"] == "The source is temporarily unavailable."
    assert (
        len((await client.get("/api/v1/events", params={"calendar_id": calendar_id})).json()) == 2
    )


async def test_subscription_rejects_private_network_url(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/calendar-subscriptions/ics/preview",
        json={"url": "http://127.0.0.1/private.ics"},
    )
    assert response.status_code == 400
    assert response.json()["code"] == "invalid_ics_subscription_url"


async def test_due_subscription_runner_refreshes_calendar(
    client: AsyncClient,
    session: AsyncSession,
    monkeypatch,
) -> None:
    install_fetch(monkeypatch, VALID_ICS)
    created = await create_subscription(client)
    calendar_id = created.json()["calendar"]["id"]
    calendar = await session.scalar(select(Calendar).where(Calendar.id == calendar_id))
    assert calendar is not None
    calendar.subscription_next_sync_at = datetime.now(UTC) - timedelta(minutes=1)
    await session.commit()
    install_fetch(monkeypatch, REFRESHED_ICS)

    await refresh_due_subscriptions()

    events = (await client.get("/api/v1/events", params={"calendar_id": calendar_id})).json()
    assert {event["title"] for event in events} == {
        "Updated planning lesson",
        "New lesson",
    }
