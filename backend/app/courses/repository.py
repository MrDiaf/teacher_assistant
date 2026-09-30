import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.courses.errors import CourseNotFoundError
from app.courses.models import Course, CourseStatus


class CourseRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list(self, status: CourseStatus | None = None) -> list[Course]:
        statement = select(Course)
        if status is not None:
            statement = statement.where(Course.status == status)
        statement = statement.order_by(Course.status, Course.created_at.desc(), Course.name)
        return list(await self.session.scalars(statement))

    async def get(self, course_id: uuid.UUID, *, for_update: bool = False) -> Course:
        statement = select(Course).where(Course.id == course_id)
        if for_update:
            statement = statement.with_for_update()
        course = await self.session.scalar(statement)
        if course is None:
            raise CourseNotFoundError()
        return course

    async def create(self, values: dict[str, Any]) -> Course:
        course = Course(**values)
        self.session.add(course)
        await self.session.flush()
        return course

    async def update(self, course_id: uuid.UUID, changes: dict[str, Any]) -> Course:
        course = await self.get(course_id, for_update=True)
        for field, value in changes.items():
            setattr(course, field, value)
        await self.session.flush()
        return course

    async def delete(self, course_id: uuid.UUID) -> None:
        course = await self.get(course_id, for_update=True)
        await self.session.delete(course)
        await self.session.flush()
