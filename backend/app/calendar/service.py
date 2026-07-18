import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.calendar.models import Calendar, CalendarEvent, CalendarSourceType
from app.calendar.repository import (
    READ_ONLY_CALENDAR_FIELDS,
    CalendarRepository,
    EventRepository,
)
from app.core.errors import (
    CalendarReadOnlyError,
    CalendarSourceProtectedError,
    InvalidEventTimeError,
)


class CalendarService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.calendars = CalendarRepository(session)
        self.events = EventRepository(session)

    async def list_calendars(self) -> list[Calendar]:
        return await self.calendars.list()

    async def get_calendar(self, calendar_id: uuid.UUID) -> Calendar:
        return await self.calendars.get(calendar_id)

    async def create_calendar(self, values: dict[str, Any]) -> Calendar:
        values = dict(values)
        source_type = values.get("source_type", CalendarSourceType.LOCAL)
        if source_type != CalendarSourceType.LOCAL:
            values["is_read_only"] = True
        calendar = await self.calendars.create(values)
        await self.session.commit()
        await self.session.refresh(calendar)
        return calendar

    async def update_calendar(self, calendar_id: uuid.UUID, changes: dict[str, Any]) -> Calendar:
        calendar = await self.calendars.get(calendar_id, for_update=True)
        self._ensure_calendar_update_allowed(calendar, changes)
        calendar = await self.calendars.update(calendar_id, changes)
        await self.session.commit()
        await self.session.refresh(calendar)
        return calendar

    async def delete_calendar(self, calendar_id: uuid.UUID) -> None:
        calendar = await self.calendars.get(calendar_id, for_update=True)
        if calendar.is_read_only:
            raise CalendarReadOnlyError()
        if calendar.source_type != CalendarSourceType.LOCAL:
            raise CalendarSourceProtectedError()
        await self.calendars.delete(calendar_id)
        await self.session.commit()

    async def list_events(
        self,
        *,
        calendar_id: uuid.UUID | None = None,
        starts_before: datetime | None = None,
        ends_after: datetime | None = None,
    ) -> list[CalendarEvent]:
        if calendar_id is not None:
            await self.calendars.get(calendar_id)
        return await self.events.list(
            calendar_id=calendar_id,
            starts_before=starts_before,
            ends_after=ends_after,
        )

    async def get_event(self, event_id: uuid.UUID) -> CalendarEvent:
        return await self.events.get(event_id)

    async def create_event(self, values: dict[str, Any]) -> CalendarEvent:
        calendar = await self.calendars.get(values["calendar_id"], for_update=True)
        self._ensure_writable(calendar)
        self._validate_event_times(values["start_at"], values["end_at"])
        event = await self.events.create(values)
        await self.session.commit()
        await self.session.refresh(event)
        return event

    async def update_event(self, event_id: uuid.UUID, changes: dict[str, Any]) -> CalendarEvent:
        event = await self.events.get(event_id, for_update=True)
        source_calendar = await self.calendars.get(event.calendar_id, for_update=True)
        self._ensure_writable(source_calendar)
        target_calendar_id = changes.get("calendar_id", event.calendar_id)
        if target_calendar_id != event.calendar_id:
            target_calendar = await self.calendars.get(target_calendar_id, for_update=True)
            self._ensure_writable(target_calendar)
        start_at = changes.get("start_at", event.start_at)
        end_at = changes.get("end_at", event.end_at)
        self._validate_event_times(start_at, end_at)
        event = await self.events.update(event_id, changes)
        await self.session.commit()
        await self.session.refresh(event)
        return event

    async def delete_event(self, event_id: uuid.UUID) -> None:
        event = await self.events.get(event_id, for_update=True)
        calendar = await self.calendars.get(event.calendar_id, for_update=True)
        self._ensure_writable(calendar)
        await self.events.delete(event_id)
        await self.session.commit()

    @staticmethod
    def _ensure_writable(calendar: Calendar) -> None:
        if calendar.is_read_only:
            raise CalendarReadOnlyError()

    @staticmethod
    def _ensure_calendar_update_allowed(calendar: Calendar, changes: dict[str, Any]) -> None:
        if (
            changes.get("is_read_only") is False
            and calendar.source_type != CalendarSourceType.LOCAL
        ):
            raise CalendarSourceProtectedError()
        if calendar.is_read_only and READ_ONLY_CALENDAR_FIELDS.intersection(changes):
            raise CalendarReadOnlyError()

    @staticmethod
    def _validate_event_times(start_at: datetime, end_at: datetime) -> None:
        if (
            start_at.tzinfo is None
            or start_at.utcoffset() is None
            or end_at.tzinfo is None
            or end_at.utcoffset() is None
            or end_at <= start_at
        ):
            raise InvalidEventTimeError()
