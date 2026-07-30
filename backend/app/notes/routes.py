import uuid
from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_session
from app.notes.schemas import NoteCreate, NoteResponse, NoteUpdate
from app.notes.service import NoteService

router = APIRouter()
SessionDependency = Annotated[AsyncSession, Depends(get_session)]


@router.get("/courses/{course_id}/notes", response_model=list[NoteResponse])
async def list_course_notes(
    course_id: uuid.UUID,
    session: SessionDependency,
) -> list[NoteResponse]:
    notes = await NoteService(session).list_notes(course_id)
    return [NoteResponse.from_note(note) for note in notes]


@router.post(
    "/courses/{course_id}/notes",
    response_model=NoteResponse,
    status_code=HTTPStatus.CREATED,
)
async def create_course_note(
    course_id: uuid.UUID,
    payload: NoteCreate,
    session: SessionDependency,
) -> NoteResponse:
    note = await NoteService(session).create_note(
        course_id,
        payload.model_dump(),
    )
    return NoteResponse.from_note(note)


@router.get("/notes/{note_id}", response_model=NoteResponse)
async def get_note(
    note_id: uuid.UUID,
    session: SessionDependency,
) -> NoteResponse:
    note = await NoteService(session).get_note(note_id)
    return NoteResponse.from_note(note)


@router.patch("/notes/{note_id}", response_model=NoteResponse)
async def update_note(
    note_id: uuid.UUID,
    payload: NoteUpdate,
    session: SessionDependency,
) -> NoteResponse:
    note = await NoteService(session).update_note(
        note_id,
        payload.model_dump(exclude_unset=True),
    )
    return NoteResponse.from_note(note)


@router.delete("/notes/{note_id}", status_code=HTTPStatus.NO_CONTENT)
async def delete_note(
    note_id: uuid.UUID,
    session: SessionDependency,
) -> Response:
    await NoteService(session).delete_note(note_id)
    return Response(status_code=HTTPStatus.NO_CONTENT)
