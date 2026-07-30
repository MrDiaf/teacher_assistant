import uuid
from datetime import datetime
from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.calendar.schemas import CalendarResponse, EventResponse
from app.course_calendars.schemas import CourseCalendarLinkCreate
from app.course_calendars.service import CourseCalendarService
from app.database.session import get_session

router = APIRouter()
SessionDependency = Annotated[AsyncSession, Depends(get_session)]


@router.get(
    "/courses/{course_id}/calendars",
    response_model=list[CalendarResponse],
)
async def list_course_calendars(
    course_id: uuid.UUID,
    session: SessionDependency,
) -> list[CalendarResponse]:
    calendars = await CourseCalendarService(session).list_calendars(course_id)
    return [CalendarResponse.model_validate(calendar) for calendar in calendars]


@router.post(
    "/courses/{course_id}/calendars",
    response_model=CalendarResponse,
    status_code=HTTPStatus.CREATED,
)
async def link_course_calendar(
    course_id: uuid.UUID,
    payload: CourseCalendarLinkCreate,
    session: SessionDependency,
) -> CalendarResponse:
    calendar = await CourseCalendarService(session).link_calendar(
        course_id,
        payload.calendar_id,
    )
    return CalendarResponse.model_validate(calendar)


@router.delete(
    "/courses/{course_id}/calendars/{calendar_id}",
    status_code=HTTPStatus.NO_CONTENT,
)
async def unlink_course_calendar(
    course_id: uuid.UUID,
    calendar_id: uuid.UUID,
    session: SessionDependency,
) -> Response:
    await CourseCalendarService(session).unlink_calendar(course_id, calendar_id)
    return Response(status_code=HTTPStatus.NO_CONTENT)


@router.get(
    "/courses/{course_id}/events",
    response_model=list[EventResponse],
)
async def list_course_events(
    course_id: uuid.UUID,
    session: SessionDependency,
    calendar_id: uuid.UUID | None = None,
    starts_before: Annotated[datetime | None, Query()] = None,
    ends_after: Annotated[datetime | None, Query()] = None,
    search: Annotated[str | None, Query(min_length=1, max_length=240)] = None,
) -> list[EventResponse]:
    events = await CourseCalendarService(session).list_events(
        course_id,
        calendar_id=calendar_id,
        starts_before=starts_before,
        ends_after=ends_after,
        search=search,
    )
    return [EventResponse.model_validate(event) for event in events]
