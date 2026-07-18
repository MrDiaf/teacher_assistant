import uuid
from datetime import datetime
from http import HTTPStatus
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.calendar.schemas import (
    CalendarCreate,
    CalendarResponse,
    CalendarUpdate,
    EventCreate,
    EventResponse,
    EventUpdate,
)
from app.calendar.service import CalendarService
from app.core.errors import InvalidRecurrenceError
from app.database.session import get_session

router = APIRouter()
SessionDependency = Annotated[AsyncSession, Depends(get_session)]


@router.get("/calendars", response_model=list[CalendarResponse])
async def list_calendars(session: SessionDependency) -> list[CalendarResponse]:
    calendars = await CalendarService(session).list_calendars()
    return [CalendarResponse.model_validate(calendar) for calendar in calendars]


@router.post("/calendars", response_model=CalendarResponse, status_code=HTTPStatus.CREATED)
async def create_calendar(payload: CalendarCreate, session: SessionDependency) -> CalendarResponse:
    calendar = await CalendarService(session).create_calendar(payload.model_dump())
    return CalendarResponse.model_validate(calendar)


@router.get("/calendars/{calendar_id}", response_model=CalendarResponse)
async def get_calendar(calendar_id: uuid.UUID, session: SessionDependency) -> CalendarResponse:
    calendar = await CalendarService(session).get_calendar(calendar_id)
    return CalendarResponse.model_validate(calendar)


@router.patch("/calendars/{calendar_id}", response_model=CalendarResponse)
async def update_calendar(
    calendar_id: uuid.UUID,
    payload: CalendarUpdate,
    session: SessionDependency,
) -> CalendarResponse:
    calendar = await CalendarService(session).update_calendar(
        calendar_id, payload.model_dump(exclude_unset=True)
    )
    return CalendarResponse.model_validate(calendar)


@router.delete("/calendars/{calendar_id}", status_code=HTTPStatus.NO_CONTENT)
async def delete_calendar(calendar_id: uuid.UUID, session: SessionDependency) -> Response:
    await CalendarService(session).delete_calendar(calendar_id)
    return Response(status_code=HTTPStatus.NO_CONTENT)


@router.get("/events", response_model=list[EventResponse])
async def list_events(
    session: SessionDependency,
    calendar_id: uuid.UUID | None = None,
    starts_before: Annotated[datetime | None, Query()] = None,
    ends_after: Annotated[datetime | None, Query()] = None,
    search: Annotated[str | None, Query(min_length=1, max_length=240)] = None,
) -> list[EventResponse]:
    events = await CalendarService(session).list_events(
        calendar_id=calendar_id,
        starts_before=starts_before,
        ends_after=ends_after,
        search=search,
    )
    return [EventResponse.model_validate(event) for event in events]


@router.post("/events", response_model=EventResponse, status_code=HTTPStatus.CREATED)
async def create_event(payload: EventCreate, session: SessionDependency) -> EventResponse:
    event = await CalendarService(session).create_event(payload.model_dump())
    return EventResponse.model_validate(event)


@router.get("/events/{event_id}", response_model=EventResponse)
async def get_event(event_id: uuid.UUID, session: SessionDependency) -> EventResponse:
    event = await CalendarService(session).get_event(event_id)
    return EventResponse.model_validate(event)


@router.patch("/events/{event_id}", response_model=EventResponse)
async def update_event(
    event_id: uuid.UUID,
    payload: EventUpdate,
    session: SessionDependency,
    recurrence_scope: Annotated[
        Literal["single", "occurrence", "series"], Query()
    ] = "single",
    occurrence_start_at: Annotated[datetime | None, Query()] = None,
) -> EventResponse:
    service = CalendarService(session)
    changes = payload.model_dump(exclude_unset=True)
    if recurrence_scope == "occurrence":
        if occurrence_start_at is None:
            raise InvalidRecurrenceError("An occurrence start time is required.")
        event = await service.update_event_occurrence(
            event_id, occurrence_start_at, changes
        )
    elif recurrence_scope == "series":
        event = await service.update_event_series(event_id, changes)
    else:
        event = await service.update_event(event_id, changes)
    return EventResponse.model_validate(event)


@router.delete("/events/{event_id}", status_code=HTTPStatus.NO_CONTENT)
async def delete_event(
    event_id: uuid.UUID,
    session: SessionDependency,
    recurrence_scope: Annotated[
        Literal["single", "occurrence", "series"], Query()
    ] = "single",
    occurrence_start_at: Annotated[datetime | None, Query()] = None,
) -> Response:
    service = CalendarService(session)
    if recurrence_scope == "occurrence":
        if occurrence_start_at is None:
            raise InvalidRecurrenceError("An occurrence start time is required.")
        await service.delete_event_occurrence(event_id, occurrence_start_at)
    elif recurrence_scope == "series":
        await service.delete_event_series(event_id)
    else:
        await service.delete_event(event_id)
    return Response(status_code=HTTPStatus.NO_CONTENT)
