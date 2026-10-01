from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends

from app.ai.schemas import AiAuthStatusResponse, AiDeviceLoginResponse, AiModelListResponse
from app.ai.service import AiModelRegistry
from app.codex_runtime.adapter import (
    CodexAuth,
    CodexDeviceLoginAttempt,
    get_codex_auth_manager,
)

router = APIRouter()
AuthDependency = Annotated[CodexAuth, Depends(get_codex_auth_manager)]


def device_login_response(attempt: CodexDeviceLoginAttempt) -> AiDeviceLoginResponse:
    return AiDeviceLoginResponse(
        login_id=attempt.login_id,
        verification_url=attempt.verification_url,
        user_code=attempt.user_code,
        status=attempt.status,
        safe_error=attempt.safe_error,
    )


@router.get("/ai/models", response_model=AiModelListResponse)
async def list_ai_models() -> AiModelListResponse:
    return AiModelRegistry().response()


@router.get("/ai/auth", response_model=AiAuthStatusResponse)
async def get_ai_auth(auth: AuthDependency) -> AiAuthStatusResponse:
    return AiAuthStatusResponse.model_validate(
        await auth.account_status(), from_attributes=True
    )


@router.post(
    "/ai/auth/device-code",
    response_model=AiDeviceLoginResponse,
    status_code=HTTPStatus.CREATED,
)
async def start_ai_device_login(auth: AuthDependency) -> AiDeviceLoginResponse:
    return device_login_response(await auth.start_device_login())


@router.get(
    "/ai/auth/device-code/{login_id}",
    response_model=AiDeviceLoginResponse,
)
async def get_ai_device_login(
    login_id: str,
    auth: AuthDependency,
) -> AiDeviceLoginResponse:
    return device_login_response(await auth.get_device_login(login_id))


@router.delete("/ai/auth", response_model=AiAuthStatusResponse)
async def logout_ai(auth: AuthDependency) -> AiAuthStatusResponse:
    return AiAuthStatusResponse.model_validate(await auth.logout(), from_attributes=True)
