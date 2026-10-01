from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


class AiModelOption(BaseModel):
    id: str
    label: str


class AiModelListResponse(BaseModel):
    default_model: str
    models: list[AiModelOption]


class AiAuthStatusResponse(BaseModel):
    authenticated: bool
    auth_type: Literal["chatgpt", "api_key"] | None
    email: str | None
    plan_type: str | None


class AiDeviceLoginResponse(BaseModel):
    login_id: str = Field(min_length=1, max_length=200)
    verification_url: HttpUrl
    user_code: str = Field(min_length=1, max_length=40)
    status: Literal["pending", "completed", "failed"]
    safe_error: str | None
