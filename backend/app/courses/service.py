import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.course_sources.storage import CourseStorage
from app.courses.models import Course, CourseSourceType, CourseStatus
from app.courses.repository import CourseRepository


class CourseService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        storage: CourseStorage | None = None,
    ) -> None:
        settings = get_settings()
        self.session = session
        self.courses = CourseRepository(session)
        self.storage = storage or CourseStorage(
            settings.course_storage_root,
            settings.course_max_upload_bytes,
            settings.course_max_upload_mb,
        )

    async def list_courses(self, status: CourseStatus | None = None) -> list[Course]:
        return await self.courses.list(status)

    async def get_course(self, course_id: uuid.UUID) -> Course:
        return await self.courses.get(course_id)

    async def create_course(self, values: dict[str, Any]) -> Course:
        creation_values = {
            **values,
            "status": CourseStatus.ACTIVE,
            "source_type": CourseSourceType.MANUAL,
        }
        course = await self.courses.create(creation_values)
        await self.session.commit()
        await self.session.refresh(course)
        await self.session.refresh(
            course,
            attribute_names=["sources", "calendar_links"],
        )
        return course

    async def update_course(self, course_id: uuid.UUID, changes: dict[str, Any]) -> Course:
        course = await self.courses.update(course_id, changes)
        await self.session.commit()
        await self.session.refresh(course)
        await self.session.refresh(
            course,
            attribute_names=["sources", "calendar_links"],
        )
        return course

    async def archive_course(self, course_id: uuid.UUID) -> Course:
        return await self._set_status(course_id, CourseStatus.ARCHIVED)

    async def restore_course(self, course_id: uuid.UUID) -> Course:
        return await self._set_status(course_id, CourseStatus.ACTIVE)

    async def delete_course(self, course_id: uuid.UUID) -> None:
        await self.courses.get(course_id, for_update=True)
        quarantine = await self.storage.quarantine_course(course_id)
        try:
            await self.courses.delete(course_id)
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            await self.storage.restore(quarantine)
            raise
        await self.storage.purge(quarantine)

    async def _set_status(self, course_id: uuid.UUID, status: CourseStatus) -> Course:
        course = await self.courses.update(course_id, {"status": status})
        await self.session.commit()
        await self.session.refresh(course)
        await self.session.refresh(
            course,
            attribute_names=["sources", "calendar_links"],
        )
        return course
