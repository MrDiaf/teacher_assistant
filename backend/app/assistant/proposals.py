from __future__ import annotations

import json
import uuid
from copy import deepcopy
from datetime import datetime
from typing import Any, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

from app.calendar.public import HEX_COLOR_PATTERN, EventStatus
from app.core.errors import InvalidAssistantResponseError


class StrictProposalModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CalendarChanges(StrictProposalModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=8000)
    color: str | None = Field(default=None, pattern=HEX_COLOR_PATTERN)
    changed_fields: list[Literal["name", "description", "color"]] | None = None

    @model_validator(mode="after")
    def require_change(self) -> CalendarChanges:
        fields = self.selected_fields()
        if not fields:
            raise ValueError("At least one supported calendar field must change.")
        if self.changed_fields is not None:
            if len(fields) != len(self.changed_fields):
                raise ValueError("Calendar changed fields must be unique.")
            for field in {"name", "description", "color"} - fields:
                if getattr(self, field) is not None:
                    raise ValueError("Unselected calendar changes must be null.")
        if ("name" in fields and self.name is None) or ("color" in fields and self.color is None):
            raise ValueError("Calendar name and color cannot be cleared.")
        return self

    def selected_fields(self) -> set[str]:
        if self.changed_fields is not None:
            return set(self.changed_fields)
        return self.model_fields_set - {"changed_fields"}

    def change_values(self, *, mode: Literal["python", "json"] = "python") -> dict[str, Any]:
        dumped = self.model_dump(mode=mode)
        return {field: dumped[field] for field in self.selected_fields()}


class ProposedEvent(StrictProposalModel):
    title: str = Field(min_length=1, max_length=240)
    description: str | None = Field(max_length=8000)
    location: str | None = Field(max_length=500)
    start_at: datetime
    end_at: datetime
    all_day: bool
    timezone: str = Field(min_length=1, max_length=64)
    recurrence_rule: str | None
    status: EventStatus

    @field_validator("start_at", "end_at")
    @classmethod
    def require_offset(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Event times must include a timezone offset.")
        return value

    @field_validator("timezone")
    @classmethod
    def require_known_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("The event timezone is not recognized.") from exc
        return value

    @model_validator(mode="after")
    def require_valid_range(self) -> ProposedEvent:
        if self.end_at <= self.start_at:
            raise ValueError("Event end time must be later than its start time.")
        return self


class EventChanges(StrictProposalModel):
    calendar_id: uuid.UUID | None = None
    title: str | None = Field(default=None, min_length=1, max_length=240)
    description: str | None = Field(default=None, max_length=8000)
    location: str | None = Field(default=None, max_length=500)
    start_at: datetime | None = None
    end_at: datetime | None = None
    all_day: bool | None = None
    timezone: str | None = Field(default=None, min_length=1, max_length=64)
    recurrence_rule: str | None = None
    status: EventStatus | None = None
    changed_fields: (
        list[
            Literal[
                "calendar_id",
                "title",
                "description",
                "location",
                "start_at",
                "end_at",
                "all_day",
                "timezone",
                "recurrence_rule",
                "status",
            ]
        ]
        | None
    ) = None

    @field_validator("start_at", "end_at")
    @classmethod
    def require_offset(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("Event times must include a timezone offset.")
        return value

    @field_validator("timezone")
    @classmethod
    def require_known_timezone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("The event timezone is not recognized.") from exc
        return value

    @model_validator(mode="after")
    def require_change(self) -> EventChanges:
        fields = self.selected_fields()
        if not fields:
            raise ValueError("At least one supported event field must change.")
        if self.changed_fields is not None:
            if len(fields) != len(self.changed_fields):
                raise ValueError("Event changed fields must be unique.")
            for field in self._supported_fields() - fields:
                if getattr(self, field) is not None:
                    raise ValueError("Unselected event changes must be null.")
        required_values = {
            "calendar_id",
            "title",
            "start_at",
            "end_at",
            "all_day",
            "timezone",
            "status",
        }
        if any(getattr(self, field) is None for field in fields & required_values):
            raise ValueError("A required event value cannot be cleared.")
        if self.start_at is not None and self.end_at is not None:
            if self.end_at <= self.start_at:
                raise ValueError("Event end time must be later than its start time.")
        return self

    @staticmethod
    def _supported_fields() -> set[str]:
        return {
            "calendar_id",
            "title",
            "description",
            "location",
            "start_at",
            "end_at",
            "all_day",
            "timezone",
            "recurrence_rule",
            "status",
        }

    def selected_fields(self) -> set[str]:
        if self.changed_fields is not None:
            return set(self.changed_fields)
        return self.model_fields_set - {"changed_fields"}

    def change_values(self, *, mode: Literal["python", "json"] = "python") -> dict[str, Any]:
        dumped = self.model_dump(mode=mode)
        return {field: dumped[field] for field in self.selected_fields()}


class CreateCalendarAction(StrictProposalModel):
    operation: Literal["create_calendar"]
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(max_length=8000)
    color: str = Field(pattern=HEX_COLOR_PATTERN)


class UpdateCalendarAction(StrictProposalModel):
    operation: Literal["update_calendar"]
    calendar_id: uuid.UUID
    changes: CalendarChanges


class CreateEventAction(StrictProposalModel):
    operation: Literal["create_event"]
    calendar_id: uuid.UUID
    event: ProposedEvent


class UpdateEventAction(StrictProposalModel):
    operation: Literal["update_event"]
    calendar_id: uuid.UUID
    event_id: uuid.UUID
    changes: EventChanges
    recurrence_scope: Literal["occurrence", "series"] | None
    occurrence_start_at: datetime | None

    @field_validator("occurrence_start_at")
    @classmethod
    def require_offset(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("Occurrence time must include a timezone offset.")
        return value


class DeleteEventAction(StrictProposalModel):
    operation: Literal["delete_event"]
    calendar_id: uuid.UUID
    event_id: uuid.UUID
    recurrence_scope: Literal["occurrence", "series"] | None
    occurrence_start_at: datetime | None

    @field_validator("occurrence_start_at")
    @classmethod
    def require_offset(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("Occurrence time must include a timezone offset.")
        return value


ProposalAction = (
    CreateCalendarAction
    | UpdateCalendarAction
    | CreateEventAction
    | UpdateEventAction
    | DeleteEventAction
)


class CalendarChangeProposal(StrictProposalModel):
    type: Literal["calendar_change"]
    summary: str = Field(min_length=1, max_length=240)
    actions: list[ProposalAction] = Field(min_length=1, max_length=10)

    @model_validator(mode="after")
    def prevent_bulk_or_mixed_deletion(self) -> CalendarChangeProposal:
        delete_count = sum(action.operation == "delete_event" for action in self.actions)
        if delete_count > 1 or (delete_count == 1 and len(self.actions) != 1):
            raise ValueError("An event deletion must be the proposal's only action.")
        return self


class CourseCitation(StrictProposalModel):
    course_id: uuid.UUID
    course_name: str = Field(min_length=1, max_length=160)
    note_id: uuid.UUID
    note_title: str = Field(min_length=1, max_length=240)
    source_id: uuid.UUID | None
    source_name: str | None = Field(default=None, min_length=1, max_length=240)
    slide_number: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def require_complete_slide_reference(self) -> CourseCitation:
        supplied = (
            self.source_id is not None,
            self.source_name is not None,
            self.slide_number is not None,
        )
        if any(supplied) and not all(supplied):
            raise ValueError("A slide citation requires source ID, source name, and slide number.")
        return self


class AssistantAnswer(StrictProposalModel):
    message: str = Field(min_length=1, max_length=8000)
    proposal: CalendarChangeProposal | None
    additional_proposals: list[CalendarChangeProposal] = Field(default_factory=list, max_length=9)
    citations: list[CourseCitation] = Field(default_factory=list, max_length=20)

    @field_validator("message")
    @classmethod
    def normalize_message(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("The assistant message cannot be blank.")
        return normalized

    @model_validator(mode="after")
    def require_safe_linked_batches(self) -> AssistantAnswer:
        if not self.additional_proposals:
            return self
        if self.proposal is None:
            raise ValueError("Linked batches require a first proposal.")
        proposals = [self.proposal, *self.additional_proposals]
        if any(
            action.operation != "create_event"
            for proposal in proposals
            for action in proposal.actions
        ):
            raise ValueError("Linked batches may contain only independent event creations.")
        return self

    def proposal_batches(self) -> list[CalendarChangeProposal]:
        if self.proposal is None:
            return []
        return [self.proposal, *self.additional_proposals]


def _strict_output_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Adapt Pydantic's schema to the strict structured-output subset."""

    strict = deepcopy(schema)

    def visit(node: Any) -> None:
        if isinstance(node, dict):
            node.pop("default", None)
            properties = node.get("properties")
            if isinstance(properties, dict):
                node["additionalProperties"] = False
                node["required"] = list(properties)
            for value in node.values():
                visit(value)
        elif isinstance(node, list):
            for value in node:
                visit(value)

    visit(strict)
    return strict


ASSISTANT_OUTPUT_SCHEMA = _strict_output_schema(AssistantAnswer.model_json_schema())


def _safe_validation_errors(error: ValidationError) -> list[dict[str, str]]:
    return [
        {
            "field": ".".join(str(item) for item in entry.get("loc", ())) or "response",
            "message": str(entry.get("msg", "Invalid value."))[:500],
            "type": str(entry.get("type", "validation_error"))[:120],
        }
        for entry in error.errors()
    ][:20]


def parse_assistant_answer(raw_response: str | None) -> AssistantAnswer:
    if raw_response is None:
        raise InvalidAssistantResponseError(
            "The model returned no final response.",
            validation_stage="response_parsing",
        )
    try:
        payload = json.loads(raw_response)
        if isinstance(payload, dict) and "citations" not in payload:
            payload["citations"] = []
        return AssistantAnswer.model_validate(payload)
    except json.JSONDecodeError as exc:
        raise InvalidAssistantResponseError(
            "The model returned malformed JSON instead of the required structured reply.",
            validation_stage="response_parsing",
            validation_errors=[
                {
                    "field": "response",
                    "message": f"Invalid JSON at line {exc.lineno}, column {exc.colno}.",
                    "type": "json_invalid",
                }
            ],
        ) from exc
    except ValidationError as exc:
        raise InvalidAssistantResponseError(
            "The response JSON did not match the required assistant answer schema.",
            validation_stage="response_schema",
            validation_errors=_safe_validation_errors(exc),
        ) from exc
