import uuid

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.course_calendars.models import CourseCalendarLink


class CourseCalendarRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_calendar_ids(self, course_id: uuid.UUID) -> tuple[uuid.UUID, ...]:
        statement = (
            select(CourseCalendarLink.calendar_id)
            .where(CourseCalendarLink.course_id == course_id)
            .order_by(CourseCalendarLink.created_at, CourseCalendarLink.id)
        )
        return tuple(await self.session.scalars(statement))

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
