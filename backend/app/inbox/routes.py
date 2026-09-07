import uuid
from http import HTTPStatus
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_session
from app.inbox.schemas import MailMessageListResponse, MailMessageResponse, MailStateUpdate
from app.inbox.service import InboxService

router = APIRouter()
SessionDependency = Annotated[AsyncSession, Depends(get_session)]


@router.get("/inbox", response_model=list[MailMessageListResponse])
async def list_inbox(
    session: SessionDependency,
    search: str | None = Query(default=None, max_length=200),
    archived: bool = False,
    unread_only: bool = False,
) -> list[MailMessageListResponse]:
    normalized = search.strip() if search else None
    return await InboxService(session).list_messages(
        search=normalized or None, archived=archived, unread_only=unread_only
    )


@router.get("/inbox/{message_id}", response_model=MailMessageResponse)
async def get_inbox_message(
    message_id: uuid.UUID, session: SessionDependency
) -> MailMessageResponse:
    return await InboxService(session).get_message(message_id)


@router.patch("/inbox/{message_id}", response_model=MailMessageResponse)
async def update_inbox_message(
    message_id: uuid.UUID,
    payload: MailStateUpdate,
    session: SessionDependency,
) -> MailMessageResponse:
    return await InboxService(session).update_state(message_id, payload)


@router.delete("/inbox/{message_id}", status_code=HTTPStatus.NO_CONTENT)
async def delete_inbox_message(message_id: uuid.UUID, session: SessionDependency) -> Response:
    await InboxService(session).delete_message(message_id)
    return Response(status_code=HTTPStatus.NO_CONTENT)


@router.get("/mail-attachments/{attachment_id}/content")
async def download_mail_attachment(
    attachment_id: uuid.UUID, session: SessionDependency
) -> FileResponse:
    item = await InboxService(session).attachment(attachment_id)
    return FileResponse(
        path=Path(item.path),
        filename=item.filename,
        media_type=item.mime_type,
        content_disposition_type="attachment",
        headers={
            "Cache-Control": "private, no-store, max-age=0",
            "Cross-Origin-Resource-Policy": "same-origin",
            "Referrer-Policy": "no-referrer",
            "X-Content-Type-Options": "nosniff",
        },
    )
