import uuid
from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_session
from app.notes.summary_schemas import NoteSummaryCreate, NoteSummaryResponse
from app.notes.summary_service import NoteSummaryService, SummaryResult
from app.platform.ai import CodexAdapter, get_codex_adapter

router = APIRouter()
SessionDependency = Annotated[AsyncSession, Depends(get_session)]
AdapterDependency = Annotated[CodexAdapter, Depends(get_codex_adapter)]


def summary_response(result: SummaryResult) -> NoteSummaryResponse:
    return NoteSummaryResponse.from_summary(
        result.summary,
        is_stale=result.is_stale,
    )


@router.get(
    "/notes/{note_id}/summary",
    response_model=NoteSummaryResponse | None,
)
async def get_latest_note_summary(
    note_id: uuid.UUID,
    session: SessionDependency,
    adapter: AdapterDependency,
) -> NoteSummaryResponse | None:
    result = await NoteSummaryService(session, adapter).latest(note_id)
    return summary_response(result) if result else None


@router.post(
    "/notes/{note_id}/summaries",
    response_model=NoteSummaryResponse,
    status_code=HTTPStatus.CREATED,
)
async def generate_note_summary(
    note_id: uuid.UUID,
    payload: NoteSummaryCreate,
    session: SessionDependency,
    adapter: AdapterDependency,
) -> NoteSummaryResponse:
    result = await NoteSummaryService(session, adapter).generate(
        note_id,
        payload.model,
    )
    return summary_response(result)


@router.post(
    "/note-summaries/{summary_id}/retry",
    response_model=NoteSummaryResponse,
)
async def retry_note_summary(
    summary_id: uuid.UUID,
    session: SessionDependency,
    adapter: AdapterDependency,
) -> NoteSummaryResponse:
    result = await NoteSummaryService(session, adapter).retry(summary_id)
    return summary_response(result)


@router.delete(
    "/note-summaries/{summary_id}/bullets/{bullet_id}",
    response_model=NoteSummaryResponse,
)
async def remove_note_summary_bullet(
    summary_id: uuid.UUID,
    bullet_id: uuid.UUID,
    session: SessionDependency,
    adapter: AdapterDependency,
) -> NoteSummaryResponse:
    result = await NoteSummaryService(session, adapter).remove_bullet(
        summary_id,
        bullet_id,
    )
    return summary_response(result)
