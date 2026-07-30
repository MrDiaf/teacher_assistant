from __future__ import annotations

import hashlib
import json
import logging
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.service import AiModelRegistry
from app.codex_runtime.adapter import CodexAdapter
from app.codex_runtime.workspace import create_summary_workspace
from app.core.errors import (
    ApplicationError,
    NoteSummaryNotRetryableError,
    NoteSummarySourceUnavailableError,
)
from app.course_sources.models import ExtractionStatus
from app.notes.models import Note
from app.notes.repository import NoteRepository
from app.notes.summary_models import NoteSummary, NoteSummaryStatus
from app.notes.summary_repository import NoteSummaryRepository
from app.notes.summary_validation import (
    SUMMARY_OUTPUT_SCHEMA,
    parse_and_validate_summary,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SummaryContext:
    note_input: dict[str, Any]
    linked_slides: list[dict[str, Any]]
    note_content_hash: str
    slide_content_hash: str
    note_available: bool
    available_slides: set[tuple[uuid.UUID, int]]
    source_error: str | None


@dataclass(frozen=True)
class SummaryResult:
    summary: NoteSummary
    is_stale: bool


class NoteSummaryService:
    def __init__(self, session: AsyncSession, adapter: CodexAdapter) -> None:
        self.session = session
        self.adapter = adapter
        self.notes = NoteRepository(session)
        self.summaries = NoteSummaryRepository(session)
        self.models = AiModelRegistry()

    async def latest(self, note_id: uuid.UUID) -> SummaryResult | None:
        note = await self.notes.get(note_id)
        summary = await self.summaries.latest_for_note(note_id)
        if summary is None:
            return None
        context = await self._build_context(note)
        is_stale = summary.status == NoteSummaryStatus.COMPLETED and (
            summary.note_content_hash != context.note_content_hash
            or summary.slide_content_hash != context.slide_content_hash
        )
        return SummaryResult(summary=summary, is_stale=is_stale)

    async def generate(
        self,
        note_id: uuid.UUID,
        requested_model: str | None,
    ) -> SummaryResult:
        model = self.models.resolve(requested_model)
        note = await self.notes.get(note_id)
        context = await self._build_context(note)
        summary = await self.summaries.create(
            note_id=note.id,
            model=model,
            note_content_hash=context.note_content_hash,
            slide_content_hash=context.slide_content_hash,
        )
        await self.session.commit()
        return await self._execute(summary.id, context)

    async def retry(self, summary_id: uuid.UUID) -> SummaryResult:
        summary = await self.summaries.get(summary_id, for_update=True)
        if summary.status != NoteSummaryStatus.FAILED:
            raise NoteSummaryNotRetryableError()
        self.models.resolve(summary.model)
        note = await self.notes.get(summary.note_id)
        context = await self._build_context(note)
        summary.status = NoteSummaryStatus.QUEUED
        summary.summary_json = None
        summary.note_content_hash = context.note_content_hash
        summary.slide_content_hash = context.slide_content_hash
        summary.safe_error = None
        summary.safe_error_code = None
        await self.session.commit()
        return await self._execute(summary.id, context)

    async def _execute(
        self,
        summary_id: uuid.UUID,
        context: SummaryContext,
    ) -> SummaryResult:
        summary = await self.summaries.update(
            summary_id,
            {
                "status": NoteSummaryStatus.RUNNING,
                "safe_error": None,
                "safe_error_code": None,
            },
        )
        await self.session.commit()
        try:
            if context.source_error:
                raise NoteSummarySourceUnavailableError(context.source_error)
            if not context.note_available and not context.linked_slides:
                raise NoteSummarySourceUnavailableError(
                    "Add note text or link slides with extracted text before summarizing."
                )
            with create_summary_workspace(
                note=context.note_input,
                linked_slides=context.linked_slides,
                output_schema=SUMMARY_OUTPUT_SCHEMA,
            ) as workspace:
                runtime_result = await self.adapter.answer(
                    workspace,
                    model=summary.model,
                )
                summary = await self.summaries.update(
                    summary.id,
                    {"status": NoteSummaryStatus.VALIDATING},
                )
                await self.session.commit()
                validated = parse_and_validate_summary(
                    runtime_result.final_response,
                    note_id=summary.note_id,
                    note_available=context.note_available,
                    available_slides=context.available_slides,
                )
            summary = await self.summaries.update(
                summary.id,
                {
                    "status": NoteSummaryStatus.COMPLETED,
                    "summary_json": validated.model_dump(mode="json"),
                    "safe_error": None,
                    "safe_error_code": None,
                },
            )
            await self.session.commit()
            await self.session.refresh(summary)
            return SummaryResult(summary=summary, is_stale=False)
        except ApplicationError as exc:
            await self.session.rollback()
            return await self._fail(summary_id, exc.message, exc.code)
        except Exception as exc:
            logger.error(
                "Unexpected note summary failure: summary=%s error_type=%s",
                summary_id,
                type(exc).__name__,
            )
            await self.session.rollback()
            return await self._fail(
                summary_id,
                "The note summary failed safely. No summary was saved. Retry safely.",
                "note_summary_internal_error",
            )

    async def _fail(
        self,
        summary_id: uuid.UUID,
        safe_error: str,
        safe_error_code: str,
    ) -> SummaryResult:
        summary = await self.summaries.update(
            summary_id,
            {
                "status": NoteSummaryStatus.FAILED,
                "summary_json": None,
                "safe_error": safe_error[:500],
                "safe_error_code": safe_error_code[:80],
            },
        )
        await self.session.commit()
        await self.session.refresh(summary)
        return SummaryResult(summary=summary, is_stale=False)

    async def _build_context(self, note: Note) -> SummaryContext:
        note_body = note.body
        note_hash = hashlib.sha256(note_body.encode("utf-8")).hexdigest()
        linked_slides: list[dict[str, Any]] = []
        hash_parts: list[dict[str, Any]] = []
        available_slides: set[tuple[uuid.UUID, int]] = set()
        unavailable_names: list[str] = []

        for link in note.slide_references:
            source = link.source
            segments = await self.summaries.list_source_text(source.id)
            selected = [
                segment
                for segment in segments
                if (
                    link.start_slide is None
                    or (link.start_slide <= segment.page_or_slide_number <= link.end_slide)
                )
            ]
            hash_parts.append(
                {
                    "source_id": str(source.id),
                    "start_slide": link.start_slide,
                    "end_slide": link.end_slide,
                    "extraction_status": source.extraction_status.value,
                    "segments": [
                        {
                            "slide": segment.page_or_slide_number,
                            "hash": segment.content_hash,
                        }
                        for segment in selected
                    ],
                }
            )
            if source.extraction_status != ExtractionStatus.COMPLETED or not selected:
                unavailable_names.append(source.display_name)
                continue
            for segment in selected:
                identity = (source.id, segment.page_or_slide_number)
                if identity in available_slides:
                    continue
                available_slides.add(identity)
                linked_slides.append(
                    {
                        "source_id": str(source.id),
                        "slide": segment.page_or_slide_number,
                        "text": segment.text,
                    }
                )

        slide_hash = hashlib.sha256(
            json.dumps(
                hash_parts,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        source_error = None
        if unavailable_names:
            names = ", ".join(dict.fromkeys(unavailable_names))
            source_error = (
                f"Linked slide text is unavailable for: {names}. "
                "Retry extraction or adjust the linked range, then retry safely."
            )
        return SummaryContext(
            note_input={"id": str(note.id), "body": note_body},
            linked_slides=linked_slides,
            note_content_hash=note_hash,
            slide_content_hash=slide_hash,
            note_available=bool(note_body.strip()),
            available_slides=available_slides,
            source_error=source_error,
        )
