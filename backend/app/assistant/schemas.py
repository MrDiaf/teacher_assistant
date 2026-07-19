import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from app.assistant.models import AssistantJobStatus, AssistantMessageRole


class ConversationCreate(BaseModel):
    title: str = Field(default="Calendar conversation", min_length=1, max_length=120)


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime


class AssistantMessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


class AssistantMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    conversation_id: uuid.UUID
    role: AssistantMessageRole
    content: str
    job_id: uuid.UUID | None
    created_at: datetime


class AssistantJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    conversation_id: uuid.UUID
    owner_message_id: uuid.UUID
    status: AssistantJobStatus
    safe_error: str | None
    created_at: datetime
    updated_at: datetime


class ConversationDetailResponse(ConversationResponse):
    messages: list[AssistantMessageResponse]
    jobs: list[AssistantJobResponse]


class AssistantTurnResponse(BaseModel):
    conversation: ConversationResponse
    owner_message: AssistantMessageResponse
    assistant_message: AssistantMessageResponse | None
    job: AssistantJobResponse


class AssistantAuthStatusResponse(BaseModel):
    authenticated: bool
    auth_type: Literal["chatgpt", "api_key"] | None
    email: str | None
    plan_type: str | None


class AssistantDeviceLoginResponse(BaseModel):
    login_id: str = Field(min_length=1, max_length=200)
    verification_url: HttpUrl
    user_code: str = Field(min_length=1, max_length=40)
    status: Literal["pending", "completed", "failed"]
    safe_error: str | None
