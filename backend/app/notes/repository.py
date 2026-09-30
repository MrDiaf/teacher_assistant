import uuid
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.courses.errors import NoteNotFoundError
from app.notes.models import Note, NoteSourceLink


class NoteRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_course(self, course_id: uuid.UUID) -> list[Note]:
        statement = (
            select(Note)
            .where(Note.course_id == course_id)
            .order_by(Note.updated_at.desc(), Note.created_at.desc())
        )
        return list(await self.session.scalars(statement))

    async def get(self, note_id: uuid.UUID, *, for_update: bool = False) -> Note:
        statement = select(Note).where(Note.id == note_id)
        if for_update:
            statement = statement.with_for_update()
        note = await self.session.scalar(statement)
        if note is None:
            raise NoteNotFoundError()
        return note

    async def create(self, values: dict[str, Any]) -> Note:
        note = Note(**values)
        self.session.add(note)
        await self.session.flush()
        await self.session.refresh(note, attribute_names=["slide_references"])
        return note

    async def update(self, note: Note, changes: dict[str, Any]) -> Note:
        for field, value in changes.items():
            setattr(note, field, value)
        await self.session.flush()
        return note

    async def replace_slide_references(
        self,
        note: Note,
        references: list[dict[str, Any]],
    ) -> Note:
        await self.session.execute(
            delete(NoteSourceLink).where(NoteSourceLink.note_id == note.id)
        )
        self.session.add_all(
            [
                NoteSourceLink(
                    note_id=note.id,
                    source_id=reference["source_id"],
                    start_slide=reference["start_slide"],
                    end_slide=reference["end_slide"],
                    label=reference["label"],
                )
                for reference in references
            ]
        )
        await self.session.flush()
        await self.session.refresh(note, attribute_names=["slide_references"])
        return note

    async def delete(self, note: Note) -> None:
        await self.session.delete(note)
        await self.session.flush()
