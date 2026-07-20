import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from app.assistant.models import (
    AssistantJobStatus,
    AssistantMessageRole,
    AssistantProposalStatus,
)
from app.assistant.proposals import ProposalAction


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
    safe_error_code: str | None
    created_at: datetime
    updated_at: datetime


class ConversationDetailResponse(ConversationResponse):
    messages: list[AssistantMessageResponse]
    jobs: list[AssistantJobResponse]
    proposals: list["AssistantProposalResponse"]


class AssistantTurnResponse(BaseModel):
    conversation: ConversationResponse
    owner_message: AssistantMessageResponse
    assistant_message: AssistantMessageResponse | None
    job: AssistantJobResponse
    proposal: "AssistantProposalResponse | None"


class ProposalReviewItem(BaseModel):
    operation: str
    title: str
    calendar_id: uuid.UUID | None
    calendar_name: str | None
    event_id: uuid.UUID | None
    event_title: str | None
    previous: dict[str, Any] | None
    proposed: dict[str, Any] | None
    recurrence_scope: Literal["occurrence", "series"] | None
    occurrence_start_at: datetime | None
    affected_events: int
    warnings: list[str]


class ProposalActionRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    position: int
    operation: str
    target_calendar_id: uuid.UUID | None
    target_event_id: uuid.UUID | None
    requested_at: datetime
    confirmed_at: datetime | None
    executed_at: datetime | None
    result: dict[str, Any] | None
    safe_error: str | None


class AssistantProposalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_id: uuid.UUID
    conversation_id: uuid.UUID
    status: AssistantProposalStatus
    summary: str
    actions: list[ProposalAction]
    review_items: list[ProposalReviewItem]
    warnings: list[str]
    affected_events: int
    expires_at: datetime
    confirmed_at: datetime | None
    rejected_at: datetime | None
    executed_at: datetime | None
    result: dict[str, Any] | None
    safe_error: str | None
    created_at: datetime
    updated_at: datetime
    action_records: list[ProposalActionRecordResponse]


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
