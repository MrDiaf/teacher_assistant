from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

if TYPE_CHECKING:
    from app.notes.models import Note, NoteSourceLink


class SlideReferenceInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: uuid.UUID
    start_slide: int | None = Field(default=None, ge=1, le=100_000)
    end_slide: int | None = Field(default=None, ge=1, le=100_000)
    label: str | None = Field(default=None, max_length=240)

    @field_validator("label")
    @classmethod
    def normalize_label(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None

    @model_validator(mode="after")
    def validate_range(self) -> SlideReferenceInput:
        if (self.start_slide is None) != (self.end_slide is None):
            raise ValueError(
                "Start slide and end slide must both be set, or both left blank."
            )
        if (
            self.start_slide is not None
            and self.end_slide is not None
            and self.end_slide < self.start_slide
        ):
            raise ValueError("End slide must be the same as or after start slide.")
        return self


class NoteCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=240)
    body: str = Field(default="", max_length=100_000)
    slide_references: list[SlideReferenceInput] = Field(
        default_factory=list,
        max_length=50,
    )

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Note title cannot be blank.")
        return normalized


class NoteUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=240)
    body: str | None = Field(default=None, max_length=100_000)
    slide_references: list[SlideReferenceInput] | None = Field(
        default=None,
        max_length=50,
    )

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("Note title cannot be blank.")
        return normalized

    @model_validator(mode="after")
    def require_a_change(self) -> NoteUpdate:
        if not self.model_fields_set:
            raise ValueError("At least one note field must be provided.")
        if "title" in self.model_fields_set and self.title is None:
            raise ValueError("Note title cannot be null.")
        if "body" in self.model_fields_set and self.body is None:
            raise ValueError("Note body cannot be null.")
        if (
            "slide_references" in self.model_fields_set
            and self.slide_references is None
        ):
            raise ValueError("Slide references cannot be null.")
        return self


class SlideReferenceResponse(BaseModel):
    id: uuid.UUID
    source_id: uuid.UUID
    source_display_name: str
    original_filename: str
    start_slide: int | None
    end_slide: int | None
    label: str | None
    created_at: datetime

    @classmethod
    def from_link(cls, link: NoteSourceLink) -> SlideReferenceResponse:
        return cls(
            id=link.id,
            source_id=link.source_id,
            source_display_name=link.source.display_name,
            original_filename=link.source.original_filename,
            start_slide=link.start_slide,
            end_slide=link.end_slide,
            label=link.label,
            created_at=link.created_at,
        )


class NoteResponse(BaseModel):
    id: uuid.UUID
    course_id: uuid.UUID
    title: str
    body: str
    slide_references: list[SlideReferenceResponse]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_note(cls, note: Note) -> NoteResponse:
        return cls(
            id=note.id,
            course_id=note.course_id,
            title=note.title,
            body=note.body,
            slide_references=[
                SlideReferenceResponse.from_link(link)
                for link in note.slide_references
            ],
            created_at=note.created_at,
            updated_at=note.updated_at,
        )
