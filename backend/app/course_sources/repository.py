import uuid
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.course_sources.extraction import ExtractedSegment
from app.course_sources.models import (
    CourseSource,
    CourseSourceType,
    ExtractedSourceText,
    ExtractionStatus,
)
from app.courses.errors import CourseSourceNotFoundError


class CourseSourceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_course(
        self,
        course_id: uuid.UUID,
        source_type: CourseSourceType | None = None,
    ) -> list[CourseSource]:
        statement = select(CourseSource).where(CourseSource.course_id == course_id)
        if source_type is not None:
            statement = statement.where(CourseSource.source_type == source_type)
        statement = statement.order_by(
            CourseSource.source_type,
            CourseSource.created_at.desc(),
        )
        return list(await self.session.scalars(statement))

    async def get(
        self,
        source_id: uuid.UUID,
        *,
        for_update: bool = False,
    ) -> CourseSource:
        statement = select(CourseSource).where(CourseSource.id == source_id)
        if for_update:
            statement = statement.with_for_update()
        source = await self.session.scalar(statement)
        if source is None:
            raise CourseSourceNotFoundError()
        return source

    async def create(self, values: dict[str, Any]) -> CourseSource:
        source = CourseSource(**values)
        self.session.add(source)
        await self.session.flush()
        await self.session.refresh(source, attribute_names=["extracted_contents"])
        return source

    async def set_extraction_status(
        self,
        source: CourseSource,
        status: ExtractionStatus,
        error: str | None = None,
    ) -> CourseSource:
        source.extraction_status = status
        source.extraction_error = error
        await self.session.flush()
        return source

    async def replace_extracted_text(
        self,
        source: CourseSource,
        segments: list[ExtractedSegment],
    ) -> CourseSource:
        await self.session.execute(
            delete(ExtractedSourceText).where(
                ExtractedSourceText.source_id == source.id
            )
        )
        source.extracted_contents = [
            ExtractedSourceText(
                source_id=source.id,
                page_or_slide_number=segment.page_or_slide_number,
                text=segment.text,
                content_hash=segment.content_hash,
            )
            for segment in segments
        ]
        await self.session.flush()
        return source

    async def delete(self, source: CourseSource) -> None:
        await self.session.delete(source)
        await self.session.flush()
