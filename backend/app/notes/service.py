import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.course_sources.models import CourseSourceType
from app.course_sources.repository import CourseSourceRepository
from app.courses.errors import CourseSourceNotFoundError, InvalidNoteSlideReferenceError
from app.courses.repository import CourseRepository
from app.notes.models import Note
from app.notes.repository import NoteRepository
from app.notes.schemas import SlideReferenceInput


class NoteService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.courses = CourseRepository(session)
        self.sources = CourseSourceRepository(session)
        self.notes = NoteRepository(session)

    async def list_notes(self, course_id: uuid.UUID) -> list[Note]:
        await self.courses.get(course_id)
        return await self.notes.list_for_course(course_id)

    async def get_note(self, note_id: uuid.UUID) -> Note:
        return await self.notes.get(note_id)

    async def create_note(
        self,
        course_id: uuid.UUID,
        values: dict[str, Any],
    ) -> Note:
        await self.courses.get(course_id)
        reference_inputs = values.pop("slide_references", [])
        references = await self._validated_references(
            course_id,
            reference_inputs,
        )
        note = await self.notes.create({**values, "course_id": course_id})
        if references:
            note = await self.notes.replace_slide_references(note, references)
        await self.session.commit()
        return await self._refresh_note(note)

    async def update_note(
        self,
        note_id: uuid.UUID,
        changes: dict[str, Any],
    ) -> Note:
        note = await self.notes.get(note_id, for_update=True)
        reference_inputs = changes.pop("slide_references", None)
        references = (
            await self._validated_references(note.course_id, reference_inputs)
            if reference_inputs is not None
            else None
        )
        if changes:
            note = await self.notes.update(note, changes)
        if references is not None:
            note = await self.notes.replace_slide_references(note, references)
        await self.session.commit()
        return await self._refresh_note(note)

    async def delete_note(self, note_id: uuid.UUID) -> None:
        note = await self.notes.get(note_id, for_update=True)
        await self.notes.delete(note)
        await self.session.commit()

    async def _validated_references(
        self,
        course_id: uuid.UUID,
        references: list[SlideReferenceInput | dict[str, Any]],
    ) -> list[dict[str, Any]]:
        validated: list[dict[str, Any]] = []
        seen: set[tuple[uuid.UUID, int | None, int | None]] = set()
        for raw_reference in references:
            reference = SlideReferenceInput.model_validate(raw_reference)
            identity = (
                reference.source_id,
                reference.start_slide,
                reference.end_slide,
            )
            if identity in seen:
                raise InvalidNoteSlideReferenceError(
                    "The same slide range cannot be linked more than once."
                )
            seen.add(identity)
            try:
                source = await self.sources.get(
                    reference.source_id,
                    for_update=True,
                )
            except CourseSourceNotFoundError as exc:
                raise InvalidNoteSlideReferenceError(
                    "A selected slide deck does not exist."
                ) from exc
            if source.course_id != course_id:
                raise InvalidNoteSlideReferenceError(
                    "A selected slide deck belongs to another course."
                )
            if source.source_type != CourseSourceType.SLIDES:
                raise InvalidNoteSlideReferenceError(
                    "Only course materials in the Slides library can be linked."
                )
            validated.append(reference.model_dump())
        return validated

    async def _refresh_note(self, note: Note) -> Note:
        await self.session.refresh(note)
        await self.session.refresh(note, attribute_names=["slide_references"])
        return note
