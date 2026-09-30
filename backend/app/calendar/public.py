"""Typed public Calendar contracts for approved feature consumers.

The adapters in this module never expose ORM objects, repositories, or their
database session.  Query adapters are read-only.  The Assistant adapter offers
only the proposal operations permitted by policy and deliberately omits
calendar deletion, protection changes, subscription controls, and bulk event
deletion.

Mutation methods flush into the caller's existing application transaction but
never commit it.  Assistant proposal confirmation is therefore able to commit
Calendar and Assistant state exactly once, while rolling the whole transaction
back on failure.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable
from datetime import datetime
from typing import Literal, Protocol, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.calendar.errors import CalendarReadOnlyError, InvalidRecurrenceError
from app.calendar.models import CalendarSourceType, EventStatus
from app.calendar.schemas import HEX_COLOR_PATTERN
from app.calendar.service import CalendarService, validate_recurrence_rule

MAX_PUBLIC_CALENDAR_IDS = 100
MAX_PUBLIC_EVENTS = 1_000


class CalendarSummary(BaseModel):
    """Bounded Calendar value returned across module boundaries."""

    model_config = ConfigDict(from_attributes=True, frozen=True)

    id: uuid.UUID
    name: str
    description: str | None
    color: str
    is_visible: bool
    is_read_only: bool
    source_type: CalendarSourceType
    is_subscribed: bool
    subscription_last_synced_at: datetime | None
    subscription_next_sync_at: datetime | None
    subscription_error: str | None
    created_at: datetime
    updated_at: datetime


class EventSummary(BaseModel):
    """Bounded event value returned across module boundaries."""

    model_config = ConfigDict(from_attributes=True, frozen=True)

    id: uuid.UUID
    calendar_id: uuid.UUID
    title: str
    description: str | None
    location: str | None
    external_uid: str | None
    start_at: datetime
    end_at: datetime
    all_day: bool
    timezone: str
    recurrence_rule: str | None
    recurrence_parent_id: uuid.UUID | None
    recurrence_original_start_at: datetime | None
    status: EventStatus
    created_at: datetime
    updated_at: datetime


class _StrictCommand(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class AssistantCalendarCreate(_StrictCommand):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=8_000)
    color: str = Field(pattern=HEX_COLOR_PATTERN)


class AssistantCalendarUpdate(_StrictCommand):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=8_000)
    color: str | None = Field(default=None, pattern=HEX_COLOR_PATTERN)

    @model_validator(mode="after")
    def require_change(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("At least one supported calendar field must change.")
        return self


class AssistantEventCreate(_StrictCommand):
    calendar_id: uuid.UUID
    title: str = Field(min_length=1, max_length=240)
    description: str | None = Field(default=None, max_length=8_000)
    location: str | None = Field(default=None, max_length=500)
    start_at: datetime
    end_at: datetime
    all_day: bool = False
    timezone: str = Field(min_length=1, max_length=64)
    recurrence_rule: str | None = None
    status: EventStatus = EventStatus.CONFIRMED

    @field_validator("start_at", "end_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Event times must include a timezone offset.")
        return value

    @model_validator(mode="after")
    def require_valid_range(self) -> Self:
        if self.end_at <= self.start_at:
            raise ValueError("Event end time must be later than its start time.")
        return self


class AssistantEventUpdate(_StrictCommand):
    calendar_id: uuid.UUID | None = None
    title: str | None = Field(default=None, min_length=1, max_length=240)
    description: str | None = Field(default=None, max_length=8_000)
    location: str | None = Field(default=None, max_length=500)
    start_at: datetime | None = None
    end_at: datetime | None = None
    all_day: bool | None = None
    timezone: str | None = Field(default=None, min_length=1, max_length=64)
    recurrence_rule: str | None = None
    status: EventStatus | None = None

    @field_validator("start_at", "end_at")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("Event times must include a timezone offset.")
        return value

    @model_validator(mode="after")
    def require_change(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("At least one supported event field must change.")
        if self.start_at is not None and self.end_at is not None:
            if self.end_at <= self.start_at:
                raise ValueError("Event end time must be later than its start time.")
        return self


class CalendarQueryPort(Protocol):
    async def list_calendars(
        self, *, calendar_ids: Iterable[uuid.UUID] | None = None
    ) -> tuple[CalendarSummary, ...]: ...

    async def get_calendar(
        self, calendar_id: uuid.UUID, *, lock_for_revalidation: bool = False
    ) -> CalendarSummary: ...

    async def list_events(
        self,
        *,
        calendar_id: uuid.UUID | None = None,
        calendar_ids: Iterable[uuid.UUID] | None = None,
        starts_before: datetime | None = None,
        ends_after: datetime | None = None,
        search: str | None = None,
        limit: int = MAX_PUBLIC_EVENTS,
    ) -> tuple[EventSummary, ...]: ...

    async def list_availability_events(
        self,
        *,
        calendar_ids: Iterable[uuid.UUID],
        starts_before: datetime,
        ends_after: datetime,
        limit: int = MAX_PUBLIC_EVENTS,
    ) -> tuple[EventSummary, ...]: ...

    async def get_event(
        self, event_id: uuid.UUID, *, lock_for_revalidation: bool = False
    ) -> EventSummary: ...


class AssistantCalendarPort(CalendarQueryPort, Protocol):
    def validate_recurrence(self, recurrence_rule: str | None) -> None: ...

    async def create_calendar(
        self, command: AssistantCalendarCreate
    ) -> CalendarSummary: ...

    async def update_calendar(
        self, calendar_id: uuid.UUID, command: AssistantCalendarUpdate
    ) -> CalendarSummary: ...

    async def create_event(self, command: AssistantEventCreate) -> EventSummary: ...

    async def update_event(
        self,
        event_id: uuid.UUID,
        command: AssistantEventUpdate,
        *,
        recurrence_scope: Literal["single", "occurrence", "series"] = "single",
        occurrence_start_at: datetime | None = None,
    ) -> EventSummary: ...

    async def delete_event(
        self,
        event_id: uuid.UUID,
        *,
        recurrence_scope: Literal["single", "occurrence", "series"] = "single",
        occurrence_start_at: datetime | None = None,
    ) -> None: ...


def _bounded_ids(values: Iterable[uuid.UUID] | None) -> tuple[uuid.UUID, ...] | None:
    if values is None:
        return None
    bounded = tuple(dict.fromkeys(values))
    if len(bounded) > MAX_PUBLIC_CALENDAR_IDS:
        raise ValueError(
            f"Calendar queries accept at most {MAX_PUBLIC_CALENDAR_IDS} calendar IDs."
        )
    return bounded


def _bounded_limit(limit: int) -> int:
    if limit < 1 or limit > MAX_PUBLIC_EVENTS:
        raise ValueError(f"Calendar queries accept a limit from 1 to {MAX_PUBLIC_EVENTS}.")
    return limit


class _CalendarQueries:
    def __init__(self, session: AsyncSession) -> None:
        self._service = CalendarService(session)

    async def list_calendars(
        self, *, calendar_ids: Iterable[uuid.UUID] | None = None
    ) -> tuple[CalendarSummary, ...]:
        selected_ids = _bounded_ids(calendar_ids)
        calendars = await self._service.list_calendars()
        if selected_ids is not None:
            by_id = {calendar.id: calendar for calendar in calendars}
            calendars = [by_id[calendar_id] for calendar_id in selected_ids if calendar_id in by_id]
        return tuple(CalendarSummary.model_validate(calendar) for calendar in calendars)

    async def get_calendar(
        self, calendar_id: uuid.UUID, *, lock_for_revalidation: bool = False
    ) -> CalendarSummary:
        calendar = await self._service.calendars.get(
            calendar_id, for_update=lock_for_revalidation
        )
        return CalendarSummary.model_validate(calendar)

    async def list_events(
        self,
        *,
        calendar_id: uuid.UUID | None = None,
        calendar_ids: Iterable[uuid.UUID] | None = None,
        starts_before: datetime | None = None,
        ends_after: datetime | None = None,
        search: str | None = None,
        limit: int = MAX_PUBLIC_EVENTS,
    ) -> tuple[EventSummary, ...]:
        selected_ids = _bounded_ids(calendar_ids)
        events = await self._service.list_events(
            calendar_id=calendar_id,
            calendar_ids=set(selected_ids) if selected_ids is not None else None,
            starts_before=starts_before,
            ends_after=ends_after,
            search=search,
            limit=_bounded_limit(limit),
        )
        return tuple(EventSummary.model_validate(event) for event in events)

    async def list_availability_events(
        self,
        *,
        calendar_ids: Iterable[uuid.UUID],
        starts_before: datetime,
        ends_after: datetime,
        limit: int = MAX_PUBLIC_EVENTS,
    ) -> tuple[EventSummary, ...]:
        return await self.list_events(
            calendar_ids=calendar_ids,
            starts_before=starts_before,
            ends_after=ends_after,
            limit=limit,
        )

    async def get_event(
        self, event_id: uuid.UUID, *, lock_for_revalidation: bool = False
    ) -> EventSummary:
        event = await self._service.events.get(
            event_id, for_update=lock_for_revalidation
        )
        return EventSummary.model_validate(event)


class _AssistantCalendarCommands(_CalendarQueries):
    def validate_recurrence(self, recurrence_rule: str | None) -> None:
        validate_recurrence_rule(recurrence_rule)

    async def create_calendar(
        self, command: AssistantCalendarCreate
    ) -> CalendarSummary:
        calendar = await self._service.create_calendar(
            {
                **command.model_dump(),
                "is_visible": True,
                "is_read_only": False,
                "source_type": CalendarSourceType.LOCAL,
            },
            commit=False,
        )
        return CalendarSummary.model_validate(calendar)

    async def update_calendar(
        self, calendar_id: uuid.UUID, command: AssistantCalendarUpdate
    ) -> CalendarSummary:
        calendar = await self._service.update_calendar(
            calendar_id,
            command.model_dump(exclude_unset=True),
            commit=False,
        )
        return CalendarSummary.model_validate(calendar)

    async def create_event(self, command: AssistantEventCreate) -> EventSummary:
        event = await self._service.create_event(command.model_dump(), commit=False)
        return EventSummary.model_validate(event)

    async def update_event(
        self,
        event_id: uuid.UUID,
        command: AssistantEventUpdate,
        *,
        recurrence_scope: Literal["single", "occurrence", "series"] = "single",
        occurrence_start_at: datetime | None = None,
    ) -> EventSummary:
        changes = command.model_dump(exclude_unset=True)
        if recurrence_scope == "occurrence":
            if occurrence_start_at is None:
                raise ValueError("Occurrence start time is required.")
            event = await self._service.update_event_occurrence(
                event_id, occurrence_start_at, changes, commit=False
            )
        elif recurrence_scope == "series":
            event = await self._service.update_event_series(
                event_id, changes, commit=False
            )
        else:
            event = await self._service.update_event(event_id, changes, commit=False)
        return EventSummary.model_validate(event)

    async def delete_event(
        self,
        event_id: uuid.UUID,
        *,
        recurrence_scope: Literal["single", "occurrence", "series"] = "single",
        occurrence_start_at: datetime | None = None,
    ) -> None:
        if recurrence_scope == "occurrence":
            if occurrence_start_at is None:
                raise ValueError("Occurrence start time is required.")
            await self._service.delete_event_occurrence(
                event_id, occurrence_start_at, commit=False
            )
        elif recurrence_scope == "series":
            await self._service.delete_event_series(event_id, commit=False)
        else:
            await self._service.delete_event(event_id, commit=False)


def calendar_query_port(session: AsyncSession) -> CalendarQueryPort:
    """Bind a read-only Calendar contract to an application transaction."""

    return _CalendarQueries(session)


def assistant_calendar_port(session: AsyncSession) -> AssistantCalendarPort:
    """Bind the restricted Assistant Calendar contract to one transaction."""

    return _AssistantCalendarCommands(session)


__all__ = [
    "AssistantCalendarCreate",
    "AssistantCalendarPort",
    "AssistantCalendarUpdate",
    "AssistantEventCreate",
    "AssistantEventUpdate",
    "CalendarQueryPort",
    "CalendarReadOnlyError",
    "CalendarSourceType",
    "CalendarSummary",
    "EventStatus",
    "EventSummary",
    "HEX_COLOR_PATTERN",
    "InvalidRecurrenceError",
    "assistant_calendar_port",
    "calendar_query_port",
]
