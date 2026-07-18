import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.calendar.models import CalendarSourceType, EventStatus

HEX_COLOR_PATTERN = r"^#[0-9a-fA-F]{6}$"


class CalendarCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None
    color: str = Field(default="#29584c", pattern=HEX_COLOR_PATTERN)
    is_visible: bool = True
    is_read_only: bool = False
    source_type: CalendarSourceType = CalendarSourceType.LOCAL


class CalendarUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None
    color: str | None = Field(default=None, pattern=HEX_COLOR_PATTERN)
    is_visible: bool | None = None
    is_read_only: bool | None = None

    @model_validator(mode="after")
    def require_a_change(self) -> "CalendarUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one calendar field must be provided.")
        return self


class CalendarResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    color: str
    is_visible: bool
    is_read_only: bool
    source_type: CalendarSourceType
    created_at: datetime
    updated_at: datetime


class EventCreate(BaseModel):
    calendar_id: uuid.UUID
    title: str = Field(min_length=1, max_length=240)
    description: str | None = None
    location: str | None = Field(default=None, max_length=500)
    start_at: datetime
    end_at: datetime
    all_day: bool = False
    timezone: str = Field(default="Europe/Stockholm", min_length=1, max_length=64)
    recurrence_rule: str | None = None
    recurrence_parent_id: uuid.UUID | None = None
    status: EventStatus = EventStatus.CONFIRMED

    @field_validator("start_at", "end_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Event times must include a timezone offset.")
        return value

    @model_validator(mode="after")
    def validate_time_range(self) -> "EventCreate":
        if self.end_at <= self.start_at:
            raise ValueError("Event end time must be later than its start time.")
        return self


class EventUpdate(BaseModel):
    calendar_id: uuid.UUID | None = None
    title: str | None = Field(default=None, min_length=1, max_length=240)
    description: str | None = None
    location: str | None = Field(default=None, max_length=500)
    start_at: datetime | None = None
    end_at: datetime | None = None
    all_day: bool | None = None
    timezone: str | None = Field(default=None, min_length=1, max_length=64)
    recurrence_rule: str | None = None
    recurrence_parent_id: uuid.UUID | None = None
    status: EventStatus | None = None

    @field_validator("start_at", "end_at")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("Event times must include a timezone offset.")
        return value

    @model_validator(mode="after")
    def require_a_change(self) -> "EventUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one event field must be provided.")
        if self.start_at is not None and self.end_at is not None and self.end_at <= self.start_at:
            raise ValueError("Event end time must be later than its start time.")
        return self


class EventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    calendar_id: uuid.UUID
    title: str
    description: str | None
    location: str | None
    start_at: datetime
    end_at: datetime
    all_day: bool
    timezone: str
    recurrence_rule: str | None
    recurrence_parent_id: uuid.UUID | None
    recurrence_original_start_at: datetime | None
    status: EventStatus
    created_at: datetime
    updated_at: datetime
