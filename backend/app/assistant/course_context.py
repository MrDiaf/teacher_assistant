from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload, selectinload

from app.core.errors import InvalidAssistantResponseError
from app.course_sources.models import CourseSourceType, ExtractionStatus
from app.courses.models import Course
from app.diagnostics.redaction import redact_text
from app.notes.models import Note, NoteSourceLink

MAX_CONTEXT_NOTES = 8
MAX_CONTEXT_SLIDES = 40
MAX_NOTE_BODY_CHARS = 8_000
MAX_NOTE_CONTEXT_CHARS = 24_000
MAX_SLIDE_TEXT_CHARS = 2_000
MAX_SLIDE_CONTEXT_CHARS = 20_000

_TOKEN_PATTERN = re.compile(r"[\w-]+", re.UNICODE)
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
_NOTE_INTENT_WORDS = {
    "anteckning",
    "anteckningar",
    "compare",
    "lecture",
    "lectures",
    "note",
    "notes",
    "slide",
    "slides",
    "summarize",
    "summary",
    "sammanfatta",
    "wrote",
    "write",
    "written",
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
    "me",
    "my",
    "note",
    "notes",
    "please",
    "show",
    "slide",
    "slides",
    "summarize",
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
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def select(self, question: str) -> CourseContextSelection:
        # Capability questions describe how note access works; they do not need any
        # private note bodies and must not accidentally become citation-required turns.
        if _is_capability_question(question):
            return self._empty()
        courses = list(
            await self.session.scalars(
                select(Course).order_by(Course.name, Course.id)
            )
        )
        if not courses:
            return self._empty()

        normalized_question = _normalized(question)
        explicit_courses = [
            course for course in courses if self._course_is_named(course, normalized_question)
        ]
        question_tokens = _tokens(question)
        question_words = set(_TOKEN_PATTERN.findall(question.casefold()))
        notes = list(
            await self.session.scalars(
                select(Note)
                .join(Course, Course.id == Note.course_id)
                .options(noload(Note.slide_references))
                .order_by(Note.updated_at.desc(), Note.id)
            )
        )
        matched_notes = [
            note
            for note in notes
            if question_tokens
            and any(token in f"{note.title} {note.body}".casefold() for token in question_tokens)
        ]
        course_by_id = {course.id: course for course in courses}
        note_intent = bool(question_words.intersection(_NOTE_INTENT_WORDS)) or bool(
            matched_notes
        )

        requires_clarification = False
        if explicit_courses:
            selected_course_ids = {course.id for course in explicit_courses[:2]}
            selected_notes: list[Note] = []
            if note_intent:
                selected_notes = [
                    note
                    for note in matched_notes
                    if note.course_id in selected_course_ids
                ]
                if not selected_notes:
                    selected_notes = [
                        note
                        for note in notes
                        if note.course_id in selected_course_ids
                    ]
        else:
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
            if note_intent and not matched_course_ids:
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
                selected_notes = [
                    note for note in notes if note.course_id == courses[0].id
                ]

        if not selected_course_ids:
            return self._empty()

        selected_courses = [
            course_by_id[course_id]
            for course_id in sorted(
                selected_course_ids,
                key=lambda item: course_by_id[item].name.casefold(),
            )
        ]
        selected_notes = selected_notes[:MAX_CONTEXT_NOTES]
        if selected_notes:
            selected_note_ids = [note.id for note in selected_notes]
            loaded_notes = list(
                await self.session.scalars(
                    select(Note)
                    .where(Note.id.in_(selected_note_ids))
                    .options(
                        selectinload(Note.slide_references).selectinload(
                            NoteSourceLink.source
                        )
                    )
                    .execution_options(populate_existing=True)
                )
            )
            loaded_by_id = {note.id: note for note in loaded_notes}
            selected_notes = [
                loaded_by_id[note_id]
                for note_id in selected_note_ids
                if note_id in loaded_by_id
            ]
        note_payloads: list[dict[str, Any]] = []
        remaining_note_chars = MAX_NOTE_CONTEXT_CHARS
        for note in selected_notes:
            body = note.body[: min(MAX_NOTE_BODY_CHARS, remaining_note_chars)]
            remaining_note_chars -= len(body)
            note_payloads.append(
                {
                    "id": str(note.id),
                    "course_id": str(note.course_id),
                    "title": redact_text(note.title),
                    "body": redact_text(body, max_length=MAX_NOTE_BODY_CHARS),
                    "updated_at": note.updated_at.isoformat(),
                }
            )
            if remaining_note_chars <= 0:
                break

        allowed_note_ids = {uuid.UUID(item["id"]) for item in note_payloads}
        references: list[dict[str, Any]] = []
        slide_text: list[dict[str, Any]] = []
        remaining_slide_chars = MAX_SLIDE_CONTEXT_CHARS
        for note in selected_notes:
            if note.id not in allowed_note_ids:
                continue
            for reference in note.slide_references:
                source = reference.source
                if (
                    source.source_type != CourseSourceType.SLIDES
                    or source.extraction_status != ExtractionStatus.COMPLETED
                ):
                    continue
                references.append(
                    {
                        "id": str(reference.id),
                        "note_id": str(note.id),
                        "source_id": str(source.id),
                        "source_name": redact_text(source.display_name),
                        "start_slide": reference.start_slide,
                        "end_slide": reference.end_slide,
                        "label": (
                            redact_text(reference.label)
                            if reference.label
                            else None
                        ),
                    }
                )
                for content in sorted(
                    source.extracted_contents,
                    key=lambda item: item.page_or_slide_number,
                ):
                    if len(slide_text) >= MAX_CONTEXT_SLIDES:
                        break
                    if (
                        reference.start_slide is not None
                        and content.page_or_slide_number < reference.start_slide
                    ) or (
                        reference.end_slide is not None
                        and content.page_or_slide_number > reference.end_slide
                    ):
                        continue
                    text = content.text[: min(MAX_SLIDE_TEXT_CHARS, remaining_slide_chars)]
                    if not text:
                        continue
                    slide_text.append(
                        {
                            "note_id": str(note.id),
                            "source_id": str(source.id),
                            "source_name": redact_text(source.display_name),
                            "slide_number": content.page_or_slide_number,
                            "text": redact_text(text),
                        }
                    )
                    remaining_slide_chars -= len(text)
                    if remaining_slide_chars <= 0:
                        break
                if len(slide_text) >= MAX_CONTEXT_SLIDES or remaining_slide_chars <= 0:
                    break
            if len(slide_text) >= MAX_CONTEXT_SLIDES or remaining_slide_chars <= 0:
                break

        return CourseContextSelection(
            courses=[self._serialize_course(item) for item in selected_courses],
            notes=note_payloads,
            slide_references=references,
            selected_slide_text=slide_text,
            requires_clarification=requires_clarification,
        )

    @staticmethod
    def _course_is_named(course: Course, normalized_question: str) -> bool:
        normalized_name = _normalized(course.name)
        padded_question = f" {normalized_question} "
        if normalized_name and f" {normalized_name} " in padded_question:
            return True
        normalized_code = _normalized(course.course_code or "")
        return bool(normalized_code and f" {normalized_code} " in padded_question)

    @staticmethod
    def _serialize_course(course: Course) -> dict[str, Any]:
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
