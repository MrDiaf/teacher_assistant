import uuid

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.calendar.models import Calendar
from app.course_calendars.models import CourseCalendarLink


class CourseCalendarRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_calendars(self, course_id: uuid.UUID) -> list[Calendar]:
        statement = (
            select(Calendar)
            .join(
                CourseCalendarLink,
                CourseCalendarLink.calendar_id == Calendar.id,
            )
            .where(CourseCalendarLink.course_id == course_id)
            .order_by(CourseCalendarLink.created_at, Calendar.name)
        )
        return list(await self.session.scalars(statement))

    async def list_calendar_ids(self, course_id: uuid.UUID) -> set[uuid.UUID]:
        statement = select(CourseCalendarLink.calendar_id).where(
            CourseCalendarLink.course_id == course_id
        )
        return set(await self.session.scalars(statement))

    async def link(self, course_id: uuid.UUID, calendar_id: uuid.UUID) -> None:
        statement = (
            insert(CourseCalendarLink)
            .values(
                id=uuid.uuid4(),
                course_id=course_id,
                calendar_id=calendar_id,
            )
            .on_conflict_do_nothing(
                constraint="uq_course_calendar_links_course_calendar"
            )
        )
        await self.session.execute(statement)
        await self.session.flush()

    async def unlink(self, course_id: uuid.UUID, calendar_id: uuid.UUID) -> None:
        await self.session.execute(
            delete(CourseCalendarLink).where(
                CourseCalendarLink.course_id == course_id,
                CourseCalendarLink.calendar_id == calendar_id,
            )
        )
        await self.session.flush()
