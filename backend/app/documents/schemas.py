import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

HEX_COLOR_PATTERN = r"^#[0-9a-fA-F]{6}$"


def normalize_required(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError("Value cannot be blank.")
    return normalized


class DocumentProjectCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=200)

    _normalize_title = field_validator("title")(normalize_required)


class DocumentProjectUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str | None = Field(default=None, min_length=1, max_length=200)

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_required(value)

    @model_validator(mode="after")
    def require_title(self) -> "DocumentProjectUpdate":
        if "title" not in self.model_fields_set or self.title is None:
            raise ValueError("A non-null project title must be provided.")
        return self


class DocumentTagCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=64)
    color: str = Field(default="#29584c", pattern=HEX_COLOR_PATTERN)

    _normalize_name = field_validator("name")(normalize_required)


class DocumentTagUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(default=None, min_length=1, max_length=64)
    color: str | None = Field(default=None, pattern=HEX_COLOR_PATTERN)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        return normalize_required(value) if value is not None else None

    @model_validator(mode="after")
    def require_change(self) -> "DocumentTagUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one tag field must be provided.")
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("Tag name cannot be null.")
        if "color" in self.model_fields_set and self.color is None:
            raise ValueError("Tag color cannot be null.")
        return self


class DocumentTagResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    color: str
    project_count: int
    created_at: datetime
    updated_at: datetime


class DocumentProjectTagResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    color: str


class DocumentProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    title: str
    tags: list[DocumentProjectTagResponse]
    created_at: datetime
    updated_at: datetime
