import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.calendar.public import (
    CalendarQueryPort,
    CalendarSummary,
    EventSummary,
    calendar_query_port,
)
from app.core.errors import CourseCalendarNotLinkedError
from app.course_calendars.repository import CourseCalendarRepository
from app.courses.repository import CourseRepository


class CourseCalendarService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.courses = CourseRepository(session)
        self.links = CourseCalendarRepository(session)
        self.calendar: CalendarQueryPort = calendar_query_port(session)

    async def list_calendars(self, course_id: uuid.UUID) -> tuple[CalendarSummary, ...]:
        await self.courses.get(course_id)
        linked_ids = await self.links.list_calendar_ids(course_id)
        return await self.calendar.list_calendars(calendar_ids=linked_ids)

    async def link_calendar(
        self,
        course_id: uuid.UUID,
        calendar_id: uuid.UUID,
    ) -> CalendarSummary:
        await self.courses.get(course_id, for_update=True)
        calendar = await self.calendar.get_calendar(
            calendar_id, lock_for_revalidation=True
        )
        await self.links.link(course_id, calendar_id)
        await self.session.commit()
        return await self.calendar.get_calendar(calendar.id)

    async def unlink_calendar(
        self,
        course_id: uuid.UUID,
        calendar_id: uuid.UUID,
    ) -> None:
        await self.courses.get(course_id, for_update=True)
        await self.calendar.get_calendar(calendar_id, lock_for_revalidation=True)
        await self.links.unlink(course_id, calendar_id)
        await self.session.commit()

    async def list_events(
        self,
        course_id: uuid.UUID,
        *,
        calendar_id: uuid.UUID | None = None,
        starts_before: datetime | None = None,
        ends_after: datetime | None = None,
        search: str | None = None,
    ) -> tuple[EventSummary, ...]:
        await self.courses.get(course_id)
        linked_ids = set(await self.links.list_calendar_ids(course_id))
        if calendar_id is not None:
            if calendar_id not in linked_ids:
                raise CourseCalendarNotLinkedError()
            linked_ids = {calendar_id}
        if not linked_ids:
            return ()
        return await self.calendar.list_events(
            calendar_ids=linked_ids,
            starts_before=starts_before,
            ends_after=ends_after,
            search=search,
        )
