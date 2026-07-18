import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.calendar.repository import CalendarRepository, EventRepository
from app.calendar.service import CalendarService
from app.core.errors import CalendarReadOnlyError
from app.database.session import session_factory


async def create_locked_event(session: AsyncSession) -> tuple[uuid.UUID, uuid.UUID]:
    service = CalendarService(session)
    calendar = await service.create_calendar(
        {
            "name": "Protected",
            "description": None,
            "color": "#29584c",
            "is_visible": True,
            "is_read_only": False,
        }
    )
    start_at = datetime(2026, 7, 20, 8, tzinfo=UTC)
    event = await service.create_event(
        {
            "calendar_id": calendar.id,
            "title": "Protected event",
            "description": None,
            "location": None,
            "start_at": start_at,
            "end_at": start_at + timedelta(hours=1),
            "all_day": False,
            "timezone": "Europe/Oslo",
            "recurrence_rule": None,
            "recurrence_parent_id": None,
        }
    )
    await service.update_calendar(calendar.id, {"is_read_only": True})
    return calendar.id, event.id


async def test_repository_rechecks_read_only_state(session: AsyncSession) -> None:
    calendar_id, event_id = await create_locked_event(session)

    with pytest.raises(CalendarReadOnlyError):
        await EventRepository(session).update(event_id, {"title": "Repository bypass"})

    with pytest.raises(CalendarReadOnlyError):
        await CalendarRepository(session).update(calendar_id, {"name": "Repository bypass"})


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE events SET title = 'SQL bypass' WHERE id = :event_id",
        "DELETE FROM events WHERE id = :event_id",
    ],
)
async def test_database_trigger_blocks_raw_event_mutation(
    session: AsyncSession, statement: str
) -> None:
    _calendar_id, event_id = await create_locked_event(session)

    with pytest.raises(DBAPIError, match="calendar_read_only"):
        await session.execute(text(statement), {"event_id": event_id})


async def test_database_trigger_blocks_raw_read_only_calendar_delete(
    session: AsyncSession,
) -> None:
    calendar_id, _event_id = await create_locked_event(session)

    with pytest.raises(DBAPIError, match="calendar_read_only"):
        await session.execute(
            text("DELETE FROM calendars WHERE id = :calendar_id"),
            {"calendar_id": calendar_id},
        )


async def test_database_trigger_blocks_raw_read_only_calendar_rename(
    session: AsyncSession,
) -> None:
    calendar_id, _event_id = await create_locked_event(session)

    with pytest.raises(DBAPIError, match="calendar_read_only"):
        await session.execute(
            text("UPDATE calendars SET name = 'SQL bypass' WHERE id = :calendar_id"),
            {"calendar_id": calendar_id},
        )


async def test_database_trigger_blocks_raw_event_creation(
    session: AsyncSession,
) -> None:
    calendar_id, _event_id = await create_locked_event(session)
    start_at = datetime(2026, 7, 21, 8, tzinfo=UTC)

    with pytest.raises(DBAPIError, match="calendar_read_only"):
        await session.execute(
            text(
                """
                INSERT INTO events (
                    id, calendar_id, title, start_at, end_at, all_day, timezone, status
                ) VALUES (
                    :id, :calendar_id, 'SQL bypass', :start_at, :end_at,
                    false, 'Europe/Oslo', 'confirmed'
                )
                """
            ),
            {
                "id": uuid.uuid4(),
                "calendar_id": calendar_id,
                "start_at": start_at,
                "end_at": start_at + timedelta(hours=1),
            },
        )


async def test_database_trigger_blocks_moving_event_out_of_read_only_calendar(
    session: AsyncSession,
) -> None:
    _calendar_id, event_id = await create_locked_event(session)
    target = await CalendarService(session).create_calendar(
        {
            "name": "Writable target",
            "description": None,
            "color": "#f4c75f",
            "is_visible": True,
            "is_read_only": False,
        }
    )

    async with session_factory() as raw_session:
        with pytest.raises(DBAPIError, match="calendar_read_only"):
            await raw_session.execute(
                text("UPDATE events SET calendar_id = :target WHERE id = :event_id"),
                {"target": target.id, "event_id": event_id},
            )


async def test_database_rejects_unfinalized_import_calendar(
    session: AsyncSession,
) -> None:
    calendar_id = uuid.uuid4()
    await session.execute(
        text(
            """
            INSERT INTO calendars (
                id, name, color, is_visible, is_read_only, is_importing, source_type
            ) VALUES (
                :calendar_id, 'Incomplete import', '#5b7fa3', true, false, true,
                'ics_import'
            )
            """
        ),
        {"calendar_id": calendar_id},
    )

    with pytest.raises(DBAPIError, match="calendar_import_not_finalized"):
        await session.commit()
