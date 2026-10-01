import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.codex_runtime.adapter import CodexAdapter, get_codex_adapter
from app.database.session import get_session
from app.diagnostics.schemas import (
    DiagnosticErrorResponse,
    DiagnosticExplainRequest,
    DiagnosticExplanationResponse,
)
from app.diagnostics.service import DiagnosticService

router = APIRouter()
SessionDependency = Annotated[AsyncSession, Depends(get_session)]
AdapterDependency = Annotated[CodexAdapter, Depends(get_codex_adapter)]


@router.get(
    "/diagnostics/errors/{error_id}",
    response_model=DiagnosticErrorResponse,
)
async def get_diagnostic_error(
    error_id: uuid.UUID,
    session: SessionDependency,
) -> DiagnosticErrorResponse:
    error = await DiagnosticService(session).get_error(error_id)
    return DiagnosticErrorResponse.model_validate(error)


@router.post(
    "/diagnostics/errors/{error_id}/explain",
    response_model=DiagnosticExplanationResponse,
)
async def explain_diagnostic_error(
    error_id: uuid.UUID,
    payload: DiagnosticExplainRequest,
    session: SessionDependency,
    adapter: AdapterDependency,
) -> DiagnosticExplanationResponse:
    error, explanation = await DiagnosticService(session, adapter).explain(
        error_id,
        model=payload.model,
    )
    return DiagnosticExplanationResponse(
        **explanation.model_dump(),
        error_id=error.id,
        request_id=error.request_id,
        model=error.explanation_model or "",
        explained_at=error.explained_at,
    )
