from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import AsyncIterable
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import CourseSourceExtractionStateError, CourseSourceNotPdfError
from app.course_sources.extraction import PDF_MIME_TYPE, ExtractionFailure, TextExtractionAdapter
from app.course_sources.models import CourseSource, CourseSourceType, ExtractionStatus
from app.course_sources.repository import CourseSourceRepository
from app.course_sources.storage import (
    CourseStorage,
    ResolvedCourseFile,
    StoredCourseFileMissingError,
)
from app.courses.repository import CourseRepository

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PdfCourseSourceContent:
    original_filename: str
    resolved_file: ResolvedCourseFile


class CourseSourceService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        storage: CourseStorage | None = None,
        extractor: TextExtractionAdapter | None = None,
    ) -> None:
        settings = get_settings()
        self.session = session
        self.courses = CourseRepository(session)
        self.sources = CourseSourceRepository(session)
        self.storage = storage or CourseStorage(
            settings.course_storage_root,
            settings.course_max_upload_bytes,
            settings.course_max_upload_mb,
        )
        self.extractor = extractor or TextExtractionAdapter()

    async def list_sources(
        self,
        course_id: uuid.UUID,
        source_type: CourseSourceType | None = None,
    ) -> list[CourseSource]:
        await self.courses.get(course_id)
        return await self.sources.list_for_course(course_id, source_type)

    async def get_source(self, source_id: uuid.UUID) -> CourseSource:
        return await self.sources.get(source_id)

    async def get_pdf_content(self, source_id: uuid.UUID) -> PdfCourseSourceContent:
        source = await self.sources.get(source_id)
        if source.mime_type != PDF_MIME_TYPE:
            raise CourseSourceNotPdfError()
        resolved_file = await self.storage.resolve_pdf_file(source)
        return PdfCourseSourceContent(
            original_filename=source.original_filename,
            resolved_file=resolved_file,
        )

    async def upload_source(
        self,
        *,
        course_id: uuid.UUID,
        source_type: CourseSourceType,
        file_name: str,
        display_name: str | None,
        chunks: AsyncIterable[bytes],
        content_length: int | None,
    ) -> CourseSource:
        await self.courses.get(course_id)
        source_id = uuid.uuid4()
        stored = await self.storage.store(
            course_id=course_id,
            source_id=source_id,
            source_type=source_type,
            file_name=file_name,
            chunks=chunks,
            content_length=content_length,
        )
        normalized_display_name = self._display_name(
            display_name,
            stored.original_filename,
        )
        supported = self.extractor.supports(stored.mime_type)
        status = (
            ExtractionStatus.NOT_STARTED
            if supported
            else ExtractionStatus.UNSUPPORTED
        )
        error = (
            None
            if supported
            else "Text extraction is unavailable for this file type."
        )
        try:
            source = await self.sources.create(
                {
                    "id": source_id,
                    "course_id": course_id,
                    "source_type": source_type,
                    "display_name": normalized_display_name,
                    "original_filename": stored.original_filename,
                    "stored_filename": stored.stored_filename,
                    "mime_type": stored.mime_type,
                    "file_size": stored.file_size,
                    "storage_path": stored.storage_path,
                    "external_id": None,
                    "content_hash": stored.content_hash,
                    "extraction_status": status,
                    "extraction_error": error,
                }
            )
            await self.session.commit()
            source = await self._refresh_source(source)
        except Exception:
            await self.session.rollback()
            await self.storage.remove_source_directory(
                course_id,
                source_type,
                source_id,
            )
            raise

        if supported:
            return await self.extract_source(source.id)
        return source

    async def extract_source(
        self,
        source_id: uuid.UUID,
        *,
        retry_only: bool = False,
    ) -> CourseSource:
        source = await self.sources.get(source_id, for_update=True)
        if retry_only and source.extraction_status != ExtractionStatus.FAILED:
            raise CourseSourceExtractionStateError(
                "Only a failed extraction can be retried."
            )
        if not self.extractor.supports(source.mime_type):
            raise CourseSourceExtractionStateError(
                "Text extraction is not supported for this file type."
            )
        if source.extraction_status == ExtractionStatus.PROCESSING:
            raise CourseSourceExtractionStateError(
                "Text extraction is already in progress."
            )
        if (
            source.extraction_status == ExtractionStatus.COMPLETED
            and source.extracted_contents
        ):
            return source

        source = await self.sources.set_extraction_status(
            source,
            ExtractionStatus.PROCESSING,
        )
        source_hash = source.content_hash
        await self.session.commit()

        try:
            path = await self.storage.resolve_source_file(source)
            segments = await asyncio.to_thread(
                self.extractor.extract,
                path,
                source.mime_type,
            )
        except (ExtractionFailure, StoredCourseFileMissingError) as exc:
            return await self._record_failure(source_id, str(exc))
        except Exception as exc:
            logger.warning(
                "course_source_extraction_failed source_id=%s error_type=%s",
                source_id,
                type(exc).__name__,
            )
            return await self._record_failure(
                source_id,
                "Text extraction failed for this file.",
            )

        current = await self.sources.get(source_id, for_update=True)
        if current.content_hash != source_hash:
            return await self._record_failure(
                source_id,
                "The stored file changed during extraction. Retry the operation.",
            )
        await self.sources.replace_extracted_text(current, segments)
        await self.sources.set_extraction_status(
            current,
            ExtractionStatus.COMPLETED,
        )
        await self.session.commit()
        return await self._refresh_source(current)

    async def retry_extraction(self, source_id: uuid.UUID) -> CourseSource:
        return await self.extract_source(source_id, retry_only=True)

    async def delete_source(self, source_id: uuid.UUID) -> None:
        source = await self.sources.get(source_id, for_update=True)
        quarantine = await self.storage.quarantine_source(source)
        try:
            await self.sources.delete(source)
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            await self.storage.restore(quarantine)
            raise
        await self.storage.purge(quarantine)

    async def _record_failure(
        self,
        source_id: uuid.UUID,
        message: str,
    ) -> CourseSource:
        source = await self.sources.get(source_id, for_update=True)
        await self.sources.set_extraction_status(
            source,
            ExtractionStatus.FAILED,
            message[:1000],
        )
        await self.session.commit()
        return await self._refresh_source(source)

    async def _refresh_source(self, source: CourseSource) -> CourseSource:
        await self.session.refresh(source)
        await self.session.refresh(source, attribute_names=["extracted_contents"])
        return source

    @staticmethod
    def _display_name(display_name: str | None, original_filename: str) -> str:
        candidate = display_name.strip() if display_name else Path(original_filename).stem
        if not candidate:
            candidate = "Course material"
        return candidate[:240]
