import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.calendar.models import Calendar, CalendarEvent
from app.calendar.repository import CalendarRepository
from app.calendar.service import CalendarService
from app.core.errors import CourseCalendarNotLinkedError
from app.course_calendars.repository import CourseCalendarRepository
from app.courses.repository import CourseRepository


class CourseCalendarService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.courses = CourseRepository(session)
        self.calendars = CalendarRepository(session)
        self.links = CourseCalendarRepository(session)
        self.calendar_service = CalendarService(session)

    async def list_calendars(self, course_id: uuid.UUID) -> list[Calendar]:
        await self.courses.get(course_id)
        return await self.links.list_calendars(course_id)

    async def link_calendar(
        self,
        course_id: uuid.UUID,
        calendar_id: uuid.UUID,
    ) -> Calendar:
        await self.courses.get(course_id, for_update=True)
        calendar = await self.calendars.get(calendar_id)
        await self.links.link(course_id, calendar_id)
        await self.session.commit()
        await self.session.refresh(calendar)
        return calendar

    async def unlink_calendar(
        self,
        course_id: uuid.UUID,
        calendar_id: uuid.UUID,
    ) -> None:
        await self.courses.get(course_id, for_update=True)
        await self.calendars.get(calendar_id)
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
    ) -> list[CalendarEvent]:
        await self.courses.get(course_id)
        linked_ids = await self.links.list_calendar_ids(course_id)
        if calendar_id is not None:
            if calendar_id not in linked_ids:
                raise CourseCalendarNotLinkedError()
            linked_ids = {calendar_id}
        if not linked_ids:
            return []
        return await self.calendar_service.list_events(
            calendar_ids=linked_ids,
            starts_before=starts_before,
            ends_after=ends_after,
            search=search,
        )
