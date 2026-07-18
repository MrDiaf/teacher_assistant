import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.calendar.schemas import CalendarResponse, EventResponse


class IcsIssueResponse(BaseModel):
    severity: Literal["warning", "error"]
    message: str


class IcsPreviewEventResponse(BaseModel):
    index: int
    uid: str | None
    title: str
    start_at: datetime | None
    end_at: datetime | None
    all_day: bool
    timezone: str
    status: str
    recurrence_rule: str | None
    is_importable: bool
    issues: list[IcsIssueResponse]


class IcsPreviewResponse(BaseModel):
    file_name: str
    suggested_calendar_name: str
    total_events: int
    importable_events: int
    skipped_events: int
    events: list[IcsPreviewEventResponse]


class IcsImportErrorResponse(BaseModel):
    index: int
    uid: str | None
    message: str


class IcsImportResponse(BaseModel):
    calendar: CalendarResponse
    imported_count: int
    duplicate_count: int
    skipped_count: int
    errors: list[IcsImportErrorResponse]
    imported_events: list[EventResponse]
    destination_calendar_id: uuid.UUID


class IcsSubscriptionPreviewRequest(BaseModel):
    url: str = Field(min_length=8, max_length=4096)


class IcsSubscriptionCreateRequest(IcsSubscriptionPreviewRequest):
    calendar_name: str | None = Field(default=None, min_length=1, max_length=120)
    calendar_color: str = Field(default="#5b7fa3", pattern=r"^#[0-9a-fA-F]{6}$")


class IcsSubscriptionSyncResponse(BaseModel):
    calendar: CalendarResponse
    created_count: int
    updated_count: int
    deleted_count: int
    skipped_count: int
