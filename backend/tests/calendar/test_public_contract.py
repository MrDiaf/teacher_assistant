import uuid
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.calendar.public import (
    AssistantCalendarCreate,
    AssistantCalendarUpdate,
    AssistantEventCreate,
    CalendarReadOnlyError,
    CalendarSummary,
    EventSummary,
    assistant_calendar_port,
    calendar_query_port,
)
from tests.helpers import create_calendar, create_event


async def test_query_contract_returns_bounded_values_for_ids_search_and_availability(
    client: AsyncClient, session: AsyncSession
) -> None:
    first = await create_calendar(client, name="Lectures")
    second = await create_calendar(client, name="Seminars")
    lecture = await create_event(client, first["id"], title="Contract lecture")
    await create_event(client, second["id"], title="Other event")
    port = calendar_query_port(session)

    calendars = await port.list_calendars(
        calendar_ids=(uuid.UUID(second["id"]), uuid.UUID(first["id"]))
    )
    assert all(isinstance(calendar, CalendarSummary) for calendar in calendars)
    assert [str(calendar.id) for calendar in calendars] == [second["id"], first["id"]]

    matching = await port.list_events(
        calendar_ids=(uuid.UUID(first["id"]),), search="contract", limit=10
    )
    assert all(isinstance(event, EventSummary) for event in matching)
    assert [str(event.id) for event in matching] == [lecture["id"]]

    availability = await port.list_availability_events(
        calendar_ids=(uuid.UUID(first["id"]),),
        starts_before=datetime(2026, 7, 21, tzinfo=UTC),
        ends_after=datetime(2026, 7, 19, tzinfo=UTC),
        limit=10,
    )
    assert [event.id for event in availability] == [uuid.UUID(lecture["id"])]

    with pytest.raises(ValueError, match="limit"):
        await port.list_events(limit=0)


async def test_assistant_contract_is_restricted_protected_and_commitless(
    client: AsyncClient, session: AsyncSession
) -> None:
    calendar = await create_calendar(client, name="Protected")
    protected = await client.patch(
        f"/api/v1/calendars/{calendar['id']}", json={"is_read_only": True}
    )
    assert protected.status_code == 200
    port = assistant_calendar_port(session)

    assert not hasattr(port, "delete_calendar")
    with pytest.raises(ValidationError):
        AssistantCalendarUpdate.model_validate({"is_read_only": False})
    with pytest.raises(CalendarReadOnlyError):
        await port.create_event(
            AssistantEventCreate(
                calendar_id=uuid.UUID(calendar["id"]),
                title="Blocked",
                start_at=datetime(2026, 7, 20, 8, tzinfo=UTC),
                end_at=datetime(2026, 7, 20, 9, tzinfo=UTC),
                timezone="Europe/Oslo",
            )
        )

    created = await port.create_calendar(
        AssistantCalendarCreate(
            name="Transactional", description=None, color="#123456"
        )
    )
    assert created.is_read_only is False
    await session.rollback()
    missing = await client.get(f"/api/v1/calendars/{created.id}")
    assert missing.status_code == 404
