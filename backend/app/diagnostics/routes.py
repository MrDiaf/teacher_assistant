import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_session
from app.diagnostics.schemas import DiagnosticErrorResponse
from app.diagnostics.service import DiagnosticService

router = APIRouter()
SessionDependency = Annotated[AsyncSession, Depends(get_session)]


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
