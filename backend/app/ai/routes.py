from fastapi import APIRouter

from app.ai.schemas import AiModelListResponse
from app.ai.service import AiModelRegistry

router = APIRouter()


@router.get("/ai/models", response_model=AiModelListResponse)
async def list_ai_models() -> AiModelListResponse:
    return AiModelRegistry().response()
