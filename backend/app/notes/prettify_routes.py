from typing import Annotated

from fastapi import APIRouter, Depends

from app.notes.prettify_schemas import NotePrettifyRequest, NotePrettifyResponse
from app.notes.prettify_service import NotePrettifyService
from app.platform.ai import CodexAdapter, get_codex_adapter

router = APIRouter()
AdapterDependency = Annotated[CodexAdapter, Depends(get_codex_adapter)]


@router.post("/notes/prettify", response_model=NotePrettifyResponse)
async def prettify_note_draft(
    payload: NotePrettifyRequest,
    adapter: AdapterDependency,
) -> NotePrettifyResponse:
    return await NotePrettifyService(adapter).suggest(payload.body, payload.model)
