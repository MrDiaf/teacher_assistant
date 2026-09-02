from typing import Annotated

from fastapi import APIRouter, Depends

from app.codex_runtime.adapter import CodexAdapter, get_codex_adapter
from app.notes.prettify_schemas import NotePrettifyRequest, NotePrettifyResponse
from app.notes.prettify_service import NotePrettifyService

router = APIRouter()
AdapterDependency = Annotated[CodexAdapter, Depends(get_codex_adapter)]


@router.post("/notes/prettify", response_model=NotePrettifyResponse)
async def prettify_note_draft(
    payload: NotePrettifyRequest,
    adapter: AdapterDependency,
) -> NotePrettifyResponse:
    return await NotePrettifyService(adapter).suggest(payload.body, payload.model)
