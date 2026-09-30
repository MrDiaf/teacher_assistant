from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import InvalidAssistantResponseError
from app.courses.public import (
    CourseContextQueryPort,
    CourseSummary,
    NoteReference,
    course_context_query_port,
)
from app.diagnostics.redaction import redact_text

MAX_CONTEXT_NOTES = 8
MAX_CONTEXT_SLIDES = 40
MAX_NOTE_BODY_CHARS = 8_000
MAX_NOTE_CONTEXT_CHARS = 24_000
MAX_SLIDE_TEXT_CHARS = 2_000
MAX_SLIDE_CONTEXT_CHARS = 20_000

_TOKEN_PATTERN = re.compile(r"\w+", re.UNICODE)
_CAPABILITY_QUESTION_PHRASES = (
    "what can you do",
    "how can you help",
    "what are you capable of",
    "what are your capabilities",
    "what is your capability",
    "what features do you have",
    "what do you support",
    "what are your limitations",
    "what can t you do",
    "what cannot you do",
    "do you have that capability",
    "do you have the capability",
)
_NOTE_CONTEXT_WORDS = {
    "anteckning",
    "anteckningar",
    "note",
    "notes",
    "slide",
    "slides",
}
_NOTE_CONTEXT_PHRASES = (
    "did i write",
    "have i written",
    "vad har jag skrivit",
    "vad skrev jag",
    "what did i write",
    "what have i written",
)
_CALENDAR_CONTEXT_WORDS = {
    "appointment",
    "appointments",
    "availability",
    "calendar",
    "calendars",
    "event",
    "events",
    "kalender",
    "kalendrar",
    "schedule",
    "scheduled",
    "scheduling",
}
_STOP_WORDS = {
    "about",
    "again",
    "assistant",
    "calendar",
    "can",
    "compare",
    "course",
    "did",
    "do",
    "explain",
    "for",
    "from",
    "have",
    "help",
    "how",
    "latest",
    "lecture",
    "lectures",
    "me",
    "my",
    "note",
    "notes",
    "please",
    "show",
    "slide",
    "slides",
    "summarize",
    "summary",
    "tell",
    "that",
    "the",
    "this",
    "tomorrow",
    "what",
    "when",
    "which",
    "with",
    "wrote",
    "write",
    "written",
    "and",
    "are",
    "you",
    "jag",
    "mina",
    "mitt",
    "och",
    "om",
    "vad",
}


def _normalized(value: str) -> str:
    return " ".join(_TOKEN_PATTERN.findall(value.casefold()))


def _tokens(value: str) -> list[str]:
    return [
        token
        for token in _TOKEN_PATTERN.findall(value.casefold())
        if len(token) >= 3 and token not in _STOP_WORDS
    ][:12]


def _is_capability_question(value: str) -> bool:
    normalized = _normalized(value)
    return any(phrase in normalized for phrase in _CAPABILITY_QUESTION_PHRASES)


def _has_explicit_note_intent(value: str) -> bool:
    words = set(_TOKEN_PATTERN.findall(value.casefold()))
    if words.intersection(_NOTE_CONTEXT_WORDS):
        return True
    normalized = _normalized(value)
    return any(phrase in normalized for phrase in _NOTE_CONTEXT_PHRASES)


def _has_explicit_calendar_intent(value: str) -> bool:
    words = set(_TOKEN_PATTERN.findall(value.casefold()))
    return bool(words.intersection(_CALENDAR_CONTEXT_WORDS))


@dataclass(frozen=True)
class CourseContextSelection:
    courses: list[dict[str, Any]]
    notes: list[dict[str, Any]]
    slide_references: list[dict[str, Any]]
    selected_slide_text: list[dict[str, Any]]
    requires_clarification: bool

    @property
    def course_ids(self) -> set[uuid.UUID]:
        return {uuid.UUID(item["id"]) for item in self.courses}

    @property
    def has_context(self) -> bool:
        return bool(self.courses)

    def audit_details(self) -> dict[str, Any]:
        return {
            "course_ids": [item["id"] for item in self.courses],
            "note_ids": [item["id"] for item in self.notes],
            "source_ids": sorted({item["source_id"] for item in self.slide_references}),
            "slide_numbers": [
                {
                    "source_id": item["source_id"],
                    "slide_number": item["slide_number"],
                }
                for item in self.selected_slide_text
            ],
            "requires_clarification": self.requires_clarification,
        }

    def validate_citations(self, citations: list[Any]) -> None:
        if self.notes and not citations:
            raise InvalidAssistantResponseError(
                "The response was given course-note context but did not include a required "
                "citation.",
                validation_stage="citation_validation",
                validation_errors=[
                    {
                        "field": "citations",
                        "message": "At least one supplied course-note citation is required.",
                        "type": "citation_missing",
                    }
                ],
            )
        courses = {item["id"]: item for item in self.courses}
        notes = {item["id"]: item for item in self.notes}
        slides = {
            (
                item["note_id"],
                item["source_id"],
                item["source_name"],
                item["slide_number"],
            )
            for item in self.selected_slide_text
        }
        seen: set[tuple[str, str, str | None, int | None]] = set()
        for index, citation in enumerate(citations):
            dumped = citation.model_dump(mode="json")
            course_id = dumped["course_id"]
            note_id = dumped["note_id"]
            course = courses.get(course_id)
            note = notes.get(note_id)
            if (
                course is None
                or note is None
                or note["course_id"] != course_id
                or course["name"] != dumped["course_name"]
                or note["title"] != dumped["note_title"]
            ):
                raise InvalidAssistantResponseError(
                    "A citation did not match the course and note context supplied to the model.",
                    validation_stage="citation_validation",
                    validation_errors=[
                        {
                            "field": f"citations.{index}",
                            "message": "Course or note identity does not match supplied context.",
                            "type": "citation_context_mismatch",
                        }
                    ],
                )
            if (
                dumped["source_id"] is not None
                and (
                    note_id,
                    dumped["source_id"],
                    dumped["source_name"],
                    dumped["slide_number"],
                )
                not in slides
            ):
                raise InvalidAssistantResponseError(
                    "A slide citation referenced slide context that was not supplied to the model.",
                    validation_stage="citation_validation",
                    validation_errors=[
                        {
                            "field": f"citations.{index}",
                            "message": "Slide identity does not match supplied context.",
                            "type": "citation_slide_mismatch",
                        }
                    ],
                )
            key = (
                course_id,
                note_id,
                dumped["source_id"],
                dumped["slide_number"],
            )
            if key in seen:
                raise InvalidAssistantResponseError(
                    "The answer returned the same citation more than once.",
                    validation_stage="citation_validation",
                    validation_errors=[
                        {
                            "field": f"citations.{index}",
                            "message": "Duplicate citations are not allowed.",
                            "type": "citation_duplicate",
                        }
                    ],
                )
            seen.add(key)


class CourseContextService:
    """Assistant-owned policy for when and which course context is relevant.

    Courses owns the records.  This service decides relevance from the owner's
    question and asks Courses' public contract for bounded, identified excerpts;
    it never queries Courses tables or receives ORM entities.
    """

    def __init__(
        self,
        session: AsyncSession,
        courses: CourseContextQueryPort | None = None,
    ) -> None:
        self.courses = courses or course_context_query_port(session)

    async def select(self, question: str) -> CourseContextSelection:
        # Capability questions describe how note access works; they do not need any
        # private note bodies and must not accidentally become citation-required turns.
        if _is_capability_question(question):
            return self._empty()
        courses = list(await self.courses.list_courses())
        if not courses:
            return self._empty()

        normalized_question = _normalized(question)
        explicit_courses = [
            course for course in courses if self._course_is_named(course, normalized_question)
        ]
        if not _has_explicit_note_intent(question):
            if explicit_courses and _has_explicit_calendar_intent(question):
                return CourseContextSelection(
                    courses=[
                        self._serialize_course(item) for item in explicit_courses[:2]
                    ],
                    notes=[],
                    slide_references=[],
                    selected_slide_text=[],
                    requires_clarification=False,
                )
            return self._empty()

        question_tokens = set(_tokens(question))
        course_by_id = {course.id: course for course in courses}

        selected_notes: list[NoteReference]
        if explicit_courses:
            selected_course_ids = {course.id for course in explicit_courses[:2]}
            selected_notes = list(
                await self.courses.find_notes(
                    course_ids=selected_course_ids,
                    match_tokens=question_tokens,
                    limit=MAX_CONTEXT_NOTES,
                )
            )
            if not selected_notes:
                selected_notes = list(
                    await self.courses.find_notes(
                        course_ids=selected_course_ids,
                        limit=MAX_CONTEXT_NOTES,
                    )
                )
        else:
            matched_notes = [
                note
                for note in await self.courses.find_notes(match_tokens=question_tokens)
                if note.course_id in course_by_id
            ]
            matched_course_ids = {note.course_id for note in matched_notes}
            if len(matched_course_ids) > 1:
                selected_courses = [
                    course_by_id[course_id]
                    for course_id in sorted(
                        matched_course_ids,
                        key=lambda item: course_by_id[item].name.casefold(),
                    )
                ]
                return CourseContextSelection(
                    courses=[self._serialize_course(item) for item in selected_courses],
                    notes=[],
                    slide_references=[],
                    selected_slide_text=[],
                    requires_clarification=True,
                )
            selected_course_ids = matched_course_ids
            selected_notes = matched_notes
            if not matched_course_ids:
                if len(courses) > 1:
                    return CourseContextSelection(
                        courses=[
                            self._serialize_course(item) for item in courses[:10]
                        ],
                        notes=[],
                        slide_references=[],
                        selected_slide_text=[],
                        requires_clarification=True,
                    )
                selected_course_ids = {courses[0].id}
                selected_notes = list(
                    await self.courses.find_notes(
                        course_ids=selected_course_ids,
                        limit=MAX_CONTEXT_NOTES,
                    )
                )

        selected_courses = [
            course_by_id[course_id]
            for course_id in sorted(
                selected_course_ids,
                key=lambda item: course_by_id[item].name.casefold(),
            )
        ]
        context = await self.courses.get_note_context(
            [note.id for note in selected_notes[:MAX_CONTEXT_NOTES]],
            max_note_body_chars=MAX_NOTE_BODY_CHARS,
            max_note_context_chars=MAX_NOTE_CONTEXT_CHARS,
            max_slides=MAX_CONTEXT_SLIDES,
            max_slide_text_chars=MAX_SLIDE_TEXT_CHARS,
            max_slide_context_chars=MAX_SLIDE_CONTEXT_CHARS,
        )

        return CourseContextSelection(
            courses=[self._serialize_course(item) for item in selected_courses],
            notes=[
                {
                    "id": str(note.id),
                    "course_id": str(note.course_id),
                    "title": redact_text(note.title),
                    "body": redact_text(note.body, max_length=MAX_NOTE_BODY_CHARS),
                    "updated_at": note.updated_at.isoformat(),
                }
                for note in context.notes
            ],
            slide_references=[
                {
                    "id": str(reference.id),
                    "note_id": str(reference.note_id),
                    "source_id": str(reference.source_id),
                    "source_name": redact_text(reference.source_name),
                    "start_slide": reference.start_slide,
                    "end_slide": reference.end_slide,
                    "label": redact_text(reference.label) if reference.label else None,
                }
                for reference in context.slide_references
            ],
            selected_slide_text=[
                {
                    "note_id": str(slide.note_id),
                    "source_id": str(slide.source_id),
                    "source_name": redact_text(slide.source_name),
                    "slide_number": slide.slide_number,
                    "text": redact_text(slide.text),
                }
                for slide in context.slide_text
            ],
            requires_clarification=False,
        )

    async def linked_calendar_ids(
        self, selection: CourseContextSelection
    ) -> set[uuid.UUID]:
        """Calendar IDs associated with the selected courses, as Courses reports them."""

        return set(await self.courses.list_linked_calendar_ids(selection.course_ids))

    @staticmethod
    def _course_is_named(course: CourseSummary, normalized_question: str) -> bool:
        normalized_name = _normalized(course.name)
        padded_question = f" {normalized_question} "
        if normalized_name and f" {normalized_name} " in padded_question:
            return True
        normalized_code = _normalized(course.course_code or "")
        return bool(normalized_code and f" {normalized_code} " in padded_question)

    @staticmethod
    def _serialize_course(course: CourseSummary) -> dict[str, Any]:
        return {
            "id": str(course.id),
            "name": redact_text(course.name),
            "course_code": (
                redact_text(course.course_code) if course.course_code else None
            ),
            "term": redact_text(course.term) if course.term else None,
            "status": course.status.value,
        }

    @staticmethod
    def _empty() -> CourseContextSelection:
        return CourseContextSelection(
            courses=[],
            notes=[],
            slide_references=[],
            selected_slide_text=[],
            requires_clarification=False,
        )
