from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_session
from app.inbox.integrations.mail.sync import MailSyncService
from app.inbox.integrations.schemas import (
    MailCheckResponse,
    MailConnectionInput,
    MailConnectionResponse,
)
from app.inbox.integrations.service import MailIntegrationService

router = APIRouter()
SessionDependency = Annotated[AsyncSession, Depends(get_session)]


@router.get("/integrations/mail", response_model=MailConnectionResponse)
async def mail_status(session: SessionDependency) -> MailConnectionResponse:
    return await MailIntegrationService(session).status()


@router.put("/integrations/mail", response_model=MailConnectionResponse)
async def connect_mail(
    payload: MailConnectionInput, session: SessionDependency
) -> MailConnectionResponse:
    return await MailIntegrationService(session).connect(payload)


@router.post("/integrations/mail/test", response_model=MailConnectionResponse)
async def test_mail(session: SessionDependency) -> MailConnectionResponse:
    return await MailIntegrationService(session).test_existing()


@router.post("/integrations/mail/check", response_model=MailCheckResponse)
async def check_mail(session: SessionDependency) -> MailCheckResponse:
    result = await MailSyncService(session).sync()
    status = await MailIntegrationService(session).status()
    return MailCheckResponse(
        imported_count=result.imported_count,
        skipped_count=result.skipped_count,
        quarantined_count=result.quarantined_count,
        status=status,
    )


@router.delete("/integrations/mail", status_code=HTTPStatus.NO_CONTENT)
async def disconnect_mail(session: SessionDependency) -> Response:
    await MailIntegrationService(session).disconnect()
    return Response(status_code=HTTPStatus.NO_CONTENT)
