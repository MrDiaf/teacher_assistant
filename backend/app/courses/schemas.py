import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.courses.models import CourseSourceType, CourseStatus

HEX_COLOR_PATTERN = r"^#[0-9a-fA-F]{6}$"


class CourseCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=160)
    course_code: str | None = Field(default=None, max_length=64)
    description: str | None = Field(default=None, max_length=5000)
    term: str | None = Field(default=None, max_length=120)
    color: str = Field(default="#29584c", pattern=HEX_COLOR_PATTERN)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Course name cannot be blank.")
        return normalized

    @field_validator("course_code", "description", "term")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None


class CourseUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=160)
    course_code: str | None = Field(default=None, max_length=64)
    description: str | None = Field(default=None, max_length=5000)
    term: str | None = Field(default=None, max_length=120)
    color: str | None = Field(default=None, pattern=HEX_COLOR_PATTERN)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("Course name cannot be blank.")
        return normalized

    @field_validator("course_code", "description", "term")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None

    @model_validator(mode="after")
    def require_a_change(self) -> "CourseUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one course field must be provided.")
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("Course name cannot be null.")
        return self


class CourseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    course_code: str | None
    description: str | None
    term: str | None
    color: str
    status: CourseStatus
    source_type: CourseSourceType
    source_count: int
    created_at: datetime
    updated_at: datetime
