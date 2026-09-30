"""Typed public Courses contracts for approved feature consumers.

The adapter in this module is read-only.  It never exposes ORM objects,
repositories, physical storage paths, or its database session, and every query
is bounded by the hard limits below regardless of what a caller requests.

Courses owns which records exist and how they relate: note ownership by course,
same-course slide links, source-type separation, and extraction state.  A
consumer decides *whether* course context is relevant to its own request, then
asks this contract for explicitly identified, bounded excerpts.  Returned values
carry the course, note, and source IDs they came from so a consumer can validate
citations against exactly what it was given.
"""

from __future__ import annotations

import re
import uuid
from collections.abc import Iterable
from datetime import datetime
from typing import Protocol

from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.course_calendars.models import CourseCalendarLink
from app.course_sources.models import CourseSourceType, ExtractionStatus
from app.courses.models import Course, CourseStatus
from app.notes.models import Note, NoteSourceLink

MAX_PUBLIC_COURSES = 500
MAX_PUBLIC_COURSE_IDS = 100
MAX_PUBLIC_MATCH_TOKENS = 12
MAX_PUBLIC_NOTE_REFERENCES = 200
MAX_PUBLIC_CONTEXT_NOTES = 8
MAX_PUBLIC_NOTE_BODY_CHARS = 8_000
MAX_PUBLIC_NOTE_CONTEXT_CHARS = 24_000
MAX_PUBLIC_CONTEXT_SLIDES = 40
MAX_PUBLIC_SLIDE_TEXT_CHARS = 2_000
MAX_PUBLIC_SLIDE_CONTEXT_CHARS = 20_000

_WORD_PATTERN = re.compile(r"\w+", re.UNICODE)


class _PublicValue(BaseModel):
    model_config = ConfigDict(frozen=True)


class CourseSummary(_PublicValue):
    """Bounded course identity returned across module boundaries."""

    id: uuid.UUID
    name: str
    course_code: str | None
    term: str | None
    status: CourseStatus


class NoteReference(_PublicValue):
    """Note identity without its body, used to discover relevant notes."""

    id: uuid.UUID
    course_id: uuid.UUID
    title: str
    updated_at: datetime


class NoteExcerpt(_PublicValue):
    """A note body truncated to the requested character budget."""

    id: uuid.UUID
    course_id: uuid.UUID
    title: str
    body: str
    updated_at: datetime


class SlideReference(_PublicValue):
    """A same-course link from a note to a completed Slides source."""

    id: uuid.UUID
    note_id: uuid.UUID
    source_id: uuid.UUID
    source_name: str
    start_slide: int | None
    end_slide: int | None
    label: str | None


class SlideExcerpt(_PublicValue):
    """Extracted text of one referenced slide, with its provenance."""

    note_id: uuid.UUID
    source_id: uuid.UUID
    source_name: str
    slide_number: int
    text: str


class NoteContext(_PublicValue):
    """Bounded note and slide excerpts for explicitly supplied note IDs."""

    notes: tuple[NoteExcerpt, ...]
    slide_references: tuple[SlideReference, ...]
    slide_text: tuple[SlideExcerpt, ...]


class CourseContextQueryPort(Protocol):
    async def list_courses(
        self, *, limit: int = MAX_PUBLIC_COURSES
    ) -> tuple[CourseSummary, ...]: ...

    async def find_notes(
        self,
        *,
        course_ids: Iterable[uuid.UUID] | None = None,
        match_tokens: Iterable[str] | None = None,
        limit: int = MAX_PUBLIC_NOTE_REFERENCES,
    ) -> tuple[NoteReference, ...]: ...

    async def get_note_context(
        self,
        note_ids: Iterable[uuid.UUID],
        *,
        max_note_body_chars: int = MAX_PUBLIC_NOTE_BODY_CHARS,
        max_note_context_chars: int = MAX_PUBLIC_NOTE_CONTEXT_CHARS,
        max_slides: int = MAX_PUBLIC_CONTEXT_SLIDES,
        max_slide_text_chars: int = MAX_PUBLIC_SLIDE_TEXT_CHARS,
        max_slide_context_chars: int = MAX_PUBLIC_SLIDE_CONTEXT_CHARS,
    ) -> NoteContext: ...

    async def list_linked_calendar_ids(
        self, course_ids: Iterable[uuid.UUID]
    ) -> tuple[uuid.UUID, ...]: ...


def _bounded(name: str, value: int, maximum: int) -> int:
    if value < 1 or value > maximum:
        raise ValueError(f"Courses queries accept {name} from 1 to {maximum}.")
    return value


def _bounded_ids(
    name: str, values: Iterable[uuid.UUID], maximum: int
) -> tuple[uuid.UUID, ...]:
    bounded = tuple(dict.fromkeys(values))
    if len(bounded) > maximum:
        raise ValueError(f"Courses queries accept at most {maximum} {name}.")
    return bounded


def _bounded_tokens(values: Iterable[str]) -> frozenset[str]:
    tokens = frozenset(value.casefold() for value in values if value)
    if len(tokens) > MAX_PUBLIC_MATCH_TOKENS:
        raise ValueError(
            f"Courses queries accept at most {MAX_PUBLIC_MATCH_TOKENS} match tokens."
        )
    return tokens


class _CourseContextQueries:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_courses(
        self, *, limit: int = MAX_PUBLIC_COURSES
    ) -> tuple[CourseSummary, ...]:
        rows = await self._session.execute(
            select(Course.id, Course.name, Course.course_code, Course.term, Course.status)
            .order_by(Course.name, Course.id)
            .limit(_bounded("a course limit", limit, MAX_PUBLIC_COURSES))
        )
        return tuple(
            CourseSummary(
                id=row.id,
                name=row.name,
                course_code=row.course_code,
                term=row.term,
                status=row.status,
            )
            for row in rows
        )

    async def find_notes(
        self,
        *,
        course_ids: Iterable[uuid.UUID] | None = None,
        match_tokens: Iterable[str] | None = None,
        limit: int = MAX_PUBLIC_NOTE_REFERENCES,
    ) -> tuple[NoteReference, ...]:
        """List note identities, newest first.

        With ``match_tokens``, only notes whose title or body contains at least
        one of the supplied whole words are returned.  Bodies are read to match
        but never leave this module through this method.
        """

        bounded_limit = _bounded("a note limit", limit, MAX_PUBLIC_NOTE_REFERENCES)
        tokens = _bounded_tokens(match_tokens) if match_tokens is not None else None
        if tokens is not None and not tokens:
            return ()
        statement = select(
            Note.id, Note.course_id, Note.title, Note.body, Note.updated_at
        ).order_by(Note.updated_at.desc(), Note.id)
        if course_ids is not None:
            selected = _bounded_ids("course IDs", course_ids, MAX_PUBLIC_COURSE_IDS)
            if not selected:
                return ()
            statement = statement.where(Note.course_id.in_(selected))
        if tokens is None:
            statement = statement.limit(bounded_limit)

        references: list[NoteReference] = []
        for row in await self._session.execute(statement):
            if tokens is not None and tokens.isdisjoint(
                _WORD_PATTERN.findall(f"{row.title} {row.body}".casefold())
            ):
                continue
            references.append(
                NoteReference(
                    id=row.id,
                    course_id=row.course_id,
                    title=row.title,
                    updated_at=row.updated_at,
                )
            )
            if len(references) >= bounded_limit:
                break
        return tuple(references)

    async def get_note_context(
        self,
        note_ids: Iterable[uuid.UUID],
        *,
        max_note_body_chars: int = MAX_PUBLIC_NOTE_BODY_CHARS,
        max_note_context_chars: int = MAX_PUBLIC_NOTE_CONTEXT_CHARS,
        max_slides: int = MAX_PUBLIC_CONTEXT_SLIDES,
        max_slide_text_chars: int = MAX_PUBLIC_SLIDE_TEXT_CHARS,
        max_slide_context_chars: int = MAX_PUBLIC_SLIDE_CONTEXT_CHARS,
    ) -> NoteContext:
        """Return excerpts for the supplied notes, in the supplied order.

        Only slide references to completed Slides sources are included, and a
        slide excerpt is returned only inside a reference's slide range.
        Literature is never returned through this contract.
        """

        selected = _bounded_ids("note IDs", note_ids, MAX_PUBLIC_CONTEXT_NOTES)
        body_limit = _bounded(
            "a note body size", max_note_body_chars, MAX_PUBLIC_NOTE_BODY_CHARS
        )
        remaining_note_chars = _bounded(
            "a note context size", max_note_context_chars, MAX_PUBLIC_NOTE_CONTEXT_CHARS
        )
        slide_limit = _bounded("a slide limit", max_slides, MAX_PUBLIC_CONTEXT_SLIDES)
        slide_text_limit = _bounded(
            "a slide text size", max_slide_text_chars, MAX_PUBLIC_SLIDE_TEXT_CHARS
        )
        remaining_slide_chars = _bounded(
            "a slide context size",
            max_slide_context_chars,
            MAX_PUBLIC_SLIDE_CONTEXT_CHARS,
        )
        if not selected:
            return NoteContext(notes=(), slide_references=(), slide_text=())

        loaded = await self._session.scalars(
            select(Note)
            .where(Note.id.in_(selected))
            .options(
                selectinload(Note.slide_references).selectinload(NoteSourceLink.source)
            )
            .execution_options(populate_existing=True)
        )
        by_id = {note.id: note for note in loaded}
        notes = [by_id[note_id] for note_id in selected if note_id in by_id]

        excerpts: list[NoteExcerpt] = []
        for note in notes:
            body = note.body[: min(body_limit, remaining_note_chars)]
            remaining_note_chars -= len(body)
            excerpts.append(
                NoteExcerpt(
                    id=note.id,
                    course_id=note.course_id,
                    title=note.title,
                    body=body,
                    updated_at=note.updated_at,
                )
            )
            if remaining_note_chars <= 0:
                break

        included = {excerpt.id for excerpt in excerpts}
        references: list[SlideReference] = []
        slide_text: list[SlideExcerpt] = []

        def exhausted() -> bool:
            return len(slide_text) >= slide_limit or remaining_slide_chars <= 0

        for note in notes:
            if note.id not in included:
                continue
            for reference in note.slide_references:
                source = reference.source
                if (
                    source.source_type != CourseSourceType.SLIDES
                    or source.extraction_status != ExtractionStatus.COMPLETED
                ):
                    continue
                references.append(
                    SlideReference(
                        id=reference.id,
                        note_id=note.id,
                        source_id=source.id,
                        source_name=source.display_name,
                        start_slide=reference.start_slide,
                        end_slide=reference.end_slide,
                        label=reference.label,
                    )
                )
                for content in sorted(
                    source.extracted_contents,
                    key=lambda item: item.page_or_slide_number,
                ):
                    if len(slide_text) >= slide_limit:
                        break
                    number = content.page_or_slide_number
                    if (
                        reference.start_slide is not None
                        and number < reference.start_slide
                    ) or (reference.end_slide is not None and number > reference.end_slide):
                        continue
                    text = content.text[: min(slide_text_limit, remaining_slide_chars)]
                    if not text:
                        continue
                    slide_text.append(
                        SlideExcerpt(
                            note_id=note.id,
                            source_id=source.id,
                            source_name=source.display_name,
                            slide_number=number,
                            text=text,
                        )
                    )
                    remaining_slide_chars -= len(text)
                    if remaining_slide_chars <= 0:
                        break
                if exhausted():
                    break
            if exhausted():
                break

        return NoteContext(
            notes=tuple(excerpts),
            slide_references=tuple(references),
            slide_text=tuple(slide_text),
        )

    async def list_linked_calendar_ids(
        self, course_ids: Iterable[uuid.UUID]
    ) -> tuple[uuid.UUID, ...]:
        """Return the Calendar IDs linked to the supplied courses.

        Courses owns only the association.  A consumer resolves the returned
        IDs through Calendar's own public contract, which remains the authority
        for calendar existence, contents, and permissions.
        """

        selected = _bounded_ids("course IDs", course_ids, MAX_PUBLIC_COURSE_IDS)
        if not selected:
            return ()
        linked = await self._session.scalars(
            select(CourseCalendarLink.calendar_id)
            .where(CourseCalendarLink.course_id.in_(selected))
            .order_by(CourseCalendarLink.created_at, CourseCalendarLink.id)
        )
        return tuple(dict.fromkeys(linked))


def course_context_query_port(session: AsyncSession) -> CourseContextQueryPort:
    """Bind the read-only Courses context contract to an application transaction."""

    return _CourseContextQueries(session)


__all__ = [
    "MAX_PUBLIC_CONTEXT_NOTES",
    "MAX_PUBLIC_CONTEXT_SLIDES",
    "MAX_PUBLIC_COURSES",
    "MAX_PUBLIC_COURSE_IDS",
    "MAX_PUBLIC_MATCH_TOKENS",
    "MAX_PUBLIC_NOTE_BODY_CHARS",
    "MAX_PUBLIC_NOTE_CONTEXT_CHARS",
    "MAX_PUBLIC_NOTE_REFERENCES",
    "MAX_PUBLIC_SLIDE_CONTEXT_CHARS",
    "MAX_PUBLIC_SLIDE_TEXT_CHARS",
    "CourseContextQueryPort",
    "CourseStatus",
    "CourseSummary",
    "NoteContext",
    "NoteExcerpt",
    "NoteReference",
    "SlideExcerpt",
    "SlideReference",
    "course_context_query_port",
]
