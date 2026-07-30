import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NoteSummaryNotFoundError
from app.course_sources.models import ExtractedSourceText
from app.notes.summary_models import NoteSummary, NoteSummaryStatus


class NoteSummaryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        note_id: uuid.UUID,
        model: str,
        note_content_hash: str,
        slide_content_hash: str,
    ) -> NoteSummary:
        summary = NoteSummary(
            note_id=note_id,
            model=model,
            status=NoteSummaryStatus.QUEUED,
            note_content_hash=note_content_hash,
            slide_content_hash=slide_content_hash,
        )
        self.session.add(summary)
        await self.session.flush()
        return summary

    async def get(
        self,
        summary_id: uuid.UUID,
        *,
        for_update: bool = False,
    ) -> NoteSummary:
        statement = select(NoteSummary).where(NoteSummary.id == summary_id)
        if for_update:
            statement = statement.with_for_update()
        summary = await self.session.scalar(statement)
        if summary is None:
            raise NoteSummaryNotFoundError()
        return summary

    async def latest_for_note(self, note_id: uuid.UUID) -> NoteSummary | None:
        statement = (
            select(NoteSummary)
            .where(NoteSummary.note_id == note_id)
            .order_by(NoteSummary.created_at.desc(), NoteSummary.id.desc())
            .limit(1)
        )
        return await self.session.scalar(statement)

    async def update(
        self,
        summary_id: uuid.UUID,
        changes: dict[str, Any],
    ) -> NoteSummary:
        summary = await self.get(summary_id, for_update=True)
        for field, value in changes.items():
            setattr(summary, field, value)
        await self.session.flush()
        return summary

    async def list_source_text(
        self,
        source_id: uuid.UUID,
    ) -> list[ExtractedSourceText]:
        statement = (
            select(ExtractedSourceText)
            .where(ExtractedSourceText.source_id == source_id)
            .order_by(ExtractedSourceText.page_or_slide_number)
        )
        return list(await self.session.scalars(statement))
