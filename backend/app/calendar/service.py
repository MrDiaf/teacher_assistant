import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.calendar.errors import (
    CalendarReadOnlyError,
    CalendarSourceProtectedError,
    InvalidEventTimeError,
    InvalidRecurrenceError,
)
from app.calendar.models import Calendar, CalendarEvent, CalendarSourceType, EventStatus
from app.calendar.repository import (
    READ_ONLY_CALENDAR_FIELDS,
    CalendarRepository,
    EventRepository,
)

ALLOWED_RECURRENCE_FREQUENCIES = {"DAILY", "WEEKLY", "MONTHLY"}
ALLOWED_RECURRENCE_PARTS = {"FREQ", "INTERVAL", "COUNT", "UNTIL", "BYDAY"}
ALLOWED_RECURRENCE_WEEKDAYS = {"MO", "TU", "WE", "TH", "FR", "SA", "SU"}


def validate_recurrence_rule(rule: str | None) -> None:
    if rule is None:
        return
    parts: dict[str, str] = {}
    for segment in rule.split(";"):
        key, separator, value = segment.partition("=")
        if not separator or not value or key in parts or key not in ALLOWED_RECURRENCE_PARTS:
            raise InvalidRecurrenceError("The recurrence rule is malformed or unsupported.")
        parts[key] = value
    frequency = parts.get("FREQ")
    if frequency not in ALLOWED_RECURRENCE_FREQUENCIES:
        raise InvalidRecurrenceError("Only daily, weekly, and monthly recurrence is supported.")
    for key, maximum in (("INTERVAL", 365), ("COUNT", 999)):
        if key in parts:
            try:
                value = int(parts[key])
            except ValueError as exc:
                raise InvalidRecurrenceError(
                    f"Recurrence {key.lower()} must be a number."
                ) from exc
            if value < 1 or value > maximum:
                raise InvalidRecurrenceError(
                    f"Recurrence {key.lower()} is outside the supported range."
                )
    if "UNTIL" in parts:
        try:
            datetime.strptime(parts["UNTIL"], "%Y%m%dT%H%M%SZ")
        except ValueError as exc:
            raise InvalidRecurrenceError(
                "Recurrence until must use UTC format YYYYMMDDTHHMMSSZ."
            ) from exc
    if "BYDAY" in parts:
        weekdays = parts["BYDAY"].split(",")
        if frequency != "WEEKLY":
            raise InvalidRecurrenceError(
                "Recurrence by-day selection is supported only for weekly events."
            )
        if len(weekdays) != len(set(weekdays)) or any(
            weekday not in ALLOWED_RECURRENCE_WEEKDAYS for weekday in weekdays
        ):
            raise InvalidRecurrenceError(
                "Weekly recurrence days must use unique MO, TU, WE, TH, FR, SA, or SU values."
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

    async def create_calendar(
        self, values: dict[str, Any], *, commit: bool = True
    ) -> Calendar:
        values = dict(values)
        source_type = values.get("source_type", CalendarSourceType.LOCAL)
        if source_type != CalendarSourceType.LOCAL:
            values["is_read_only"] = True
        calendar = await self.calendars.create(values)
        if commit:
            await self.session.commit()
            await self.session.refresh(calendar)
        else:
            await self.session.refresh(calendar)
        return calendar

    async def update_calendar(
        self,
        calendar_id: uuid.UUID,
        changes: dict[str, Any],
        *,
        commit: bool = True,
    ) -> Calendar:
        calendar = await self.calendars.get(calendar_id, for_update=True)
        self._ensure_calendar_update_allowed(calendar, changes)
        calendar = await self.calendars.update(calendar_id, changes)
        if commit:
            await self.session.commit()
            await self.session.refresh(calendar)
        else:
            await self.session.refresh(calendar)
        return calendar

    async def delete_calendar(
        self, calendar_id: uuid.UUID, *, commit: bool = True
    ) -> None:
        calendar = await self.calendars.get(calendar_id, for_update=True)
        if calendar.is_read_only:
            raise CalendarReadOnlyError()
        if calendar.source_type != CalendarSourceType.LOCAL:
            raise CalendarSourceProtectedError()
        await self.calendars.delete(calendar_id)
        if commit:
            await self.session.commit()

    async def list_events(
        self,
        *,
        calendar_id: uuid.UUID | None = None,
        calendar_ids: set[uuid.UUID] | None = None,
        starts_before: datetime | None = None,
        ends_after: datetime | None = None,
        search: str | None = None,
        limit: int | None = None,
    ) -> list[CalendarEvent]:
        if calendar_id is not None:
            await self.calendars.get(calendar_id)
        events = await self.events.list(
            calendar_id=calendar_id,
            calendar_ids=calendar_ids,
            starts_before=starts_before,
            ends_after=ends_after,
            limit=limit,
        )
        if not search:
            return events
        query = search.casefold().strip()
        matching_series_ids = {
            event.recurrence_parent_id or event.id
            for event in events
            if self._event_matches(event, query)
            and (event.recurrence_rule or event.recurrence_parent_id)
        }
        return [
            event
            for event in events
            if self._event_matches(event, query)
            or (event.recurrence_parent_id or event.id) in matching_series_ids
        ]

    async def get_event(self, event_id: uuid.UUID) -> CalendarEvent:
        return await self.events.get(event_id)

    async def create_event(
        self, values: dict[str, Any], *, commit: bool = True
    ) -> CalendarEvent:
        calendar = await self.calendars.get(values["calendar_id"], for_update=True)
        self._ensure_writable(calendar)
        self._validate_event_times(values["start_at"], values["end_at"])
        validate_recurrence_rule(values.get("recurrence_rule"))
        event = await self.events.create(values)
        if commit:
            await self.session.commit()
            await self.session.refresh(event)
        else:
            await self.session.refresh(event)
        return event

    async def update_event(
        self,
        event_id: uuid.UUID,
        changes: dict[str, Any],
        *,
        commit: bool = True,
    ) -> CalendarEvent:
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
        validate_recurrence_rule(changes.get("recurrence_rule", event.recurrence_rule))
        event = await self.events.update(event_id, changes)
        if commit:
            await self.session.commit()
            await self.session.refresh(event)
        else:
            await self.session.refresh(event)
        return event

    async def delete_event(self, event_id: uuid.UUID, *, commit: bool = True) -> None:
        event = await self.events.get(event_id, for_update=True)
        calendar = await self.calendars.get(event.calendar_id, for_update=True)
        self._ensure_writable(calendar)
        await self.events.delete(event_id)
        if commit:
            await self.session.commit()

    async def update_event_occurrence(
        self,
        event_id: uuid.UUID,
        occurrence_start_at: datetime,
        changes: dict[str, Any],
        *,
        commit: bool = True,
    ) -> CalendarEvent:
        self._require_timezone(occurrence_start_at)
        parent = await self._get_series_parent(event_id)
        calendar = await self.calendars.get(parent.calendar_id, for_update=True)
        self._ensure_writable(calendar)
        if changes.get("calendar_id", parent.calendar_id) != parent.calendar_id:
            raise InvalidRecurrenceError(
                "One occurrence cannot move to another calendar; move the complete series instead."
            )

        existing = await self.events.get_exception(
            parent.id, occurrence_start_at, for_update=True
        )
        duration = parent.end_at - parent.start_at
        source = existing or parent
        values: dict[str, Any] = {
            "calendar_id": parent.calendar_id,
            "title": source.title,
            "description": source.description,
            "location": source.location,
            "start_at": existing.start_at if existing else occurrence_start_at,
            "end_at": existing.end_at if existing else occurrence_start_at + duration,
            "all_day": source.all_day,
            "timezone": source.timezone,
            "recurrence_rule": None,
            "recurrence_parent_id": parent.id,
            "recurrence_original_start_at": occurrence_start_at,
            "status": source.status,
        }
        values.update(changes)
        values["calendar_id"] = parent.calendar_id
        values["recurrence_rule"] = None
        values["recurrence_parent_id"] = parent.id
        values["recurrence_original_start_at"] = occurrence_start_at
        self._validate_event_times(values["start_at"], values["end_at"])

        if existing is None:
            occurrence = await self.events.create(values)
        else:
            occurrence = await self.events.update(existing.id, values)
        if commit:
            await self.session.commit()
            await self.session.refresh(occurrence)
        else:
            await self.session.refresh(occurrence)
        return occurrence

    async def update_event_series(
        self,
        event_id: uuid.UUID,
        changes: dict[str, Any],
        *,
        commit: bool = True,
    ) -> CalendarEvent:
        parent = await self._get_series_parent(event_id)
        validate_recurrence_rule(changes.get("recurrence_rule", parent.recurrence_rule))
        source_calendar_id = parent.calendar_id
        original_start_at = parent.start_at
        original_recurrence_rule = parent.recurrence_rule
        source_calendar = await self.calendars.get(source_calendar_id, for_update=True)
        self._ensure_writable(source_calendar)
        target_calendar_id = changes.get("calendar_id", parent.calendar_id)
        if target_calendar_id != parent.calendar_id:
            target = await self.calendars.get(target_calendar_id, for_update=True)
            self._ensure_writable(target)

        start_at = changes.get("start_at", parent.start_at)
        end_at = changes.get("end_at", parent.end_at)
        self._validate_event_times(start_at, end_at)
        updated = await self.events.update(parent.id, changes)
        resets_exceptions = (
            changes.get("start_at", original_start_at) != original_start_at
            or (
                "recurrence_rule" in changes
                and changes["recurrence_rule"] != original_recurrence_rule
            )
        )
        if resets_exceptions:
            await self.events.delete_exceptions(parent.id)
        elif target_calendar_id != source_calendar_id:
            for exception in await self.events.list_exceptions(parent.id):
                await self.events.update(exception.id, {"calendar_id": target_calendar_id})
        if commit:
            await self.session.commit()
            await self.session.refresh(updated)
        else:
            await self.session.refresh(updated)
        return updated

    async def delete_event_occurrence(
        self,
        event_id: uuid.UUID,
        occurrence_start_at: datetime,
        *,
        commit: bool = True,
    ) -> None:
        self._require_timezone(occurrence_start_at)
        parent = await self._get_series_parent(event_id)
        await self.update_event_occurrence(
            parent.id,
            occurrence_start_at,
            {"status": EventStatus.CANCELLED},
            commit=commit,
        )

    async def delete_event_series(
        self, event_id: uuid.UUID, *, commit: bool = True
    ) -> None:
        parent = await self._get_series_parent(event_id)
        await self.events.delete_series(parent.id)
        if commit:
            await self.session.commit()

    async def _get_series_parent(self, event_id: uuid.UUID) -> CalendarEvent:
        event = await self.events.get(event_id, for_update=True)
        parent = (
            await self.events.get(event.recurrence_parent_id, for_update=True)
            if event.recurrence_parent_id
            else event
        )
        if not parent.recurrence_rule:
            raise InvalidRecurrenceError("The requested event is not a recurring series.")
        return parent

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

    @staticmethod
    def _require_timezone(value: datetime) -> None:
        if value.tzinfo is None or value.utcoffset() is None:
            raise InvalidRecurrenceError("Occurrence time must include a timezone offset.")

    @staticmethod
    def _event_matches(event: CalendarEvent, query: str) -> bool:
        return any(
            query in (value or "").casefold()
            for value in (event.title, event.description, event.location)
        )
