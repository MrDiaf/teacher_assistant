from __future__ import annotations

import uuid
from copy import deepcopy
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from app.core.errors import InvalidDiagnosticExplanationError


class DiagnosticExplanation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plain_explanation: str = Field(min_length=1, max_length=2_000)
    likely_cause: str = Field(min_length=1, max_length=2_000)
    input_fixes: list[str] = Field(max_length=10)
    application_improvements: list[str] = Field(max_length=10)
    retry_is_safe: bool

    @field_validator(
        "plain_explanation",
        "likely_cause",
    )
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("input_fixes", "application_improvements")
    @classmethod
    def normalize_items(cls, value: list[str]) -> list[str]:
        normalized = [item.strip() for item in value if item.strip()]
        if any(len(item) > 1_000 for item in normalized):
            raise ValueError("Diagnostic suggestions must be concise.")
        return normalized


def _strict_output_schema(schema: dict[str, Any]) -> dict[str, Any]:
    strict = deepcopy(schema)

    def visit(node: Any) -> None:
        if isinstance(node, dict):
            node.pop("default", None)
            properties = node.get("properties")
            if isinstance(properties, dict):
                node["additionalProperties"] = False
                node["required"] = list(properties)
            for child in node.values():
                visit(child)
        elif isinstance(node, list):
            for child in node:
                visit(child)

    visit(strict)
    return strict


DIAGNOSTIC_OUTPUT_SCHEMA = _strict_output_schema(DiagnosticExplanation.model_json_schema())


def parse_diagnostic_explanation(raw_response: str | None) -> DiagnosticExplanation:
    if raw_response is None:
        raise InvalidDiagnosticExplanationError()
    try:
        return DiagnosticExplanation.model_validate_json(raw_response)
    except ValidationError as exc:
        raise InvalidDiagnosticExplanationError() from exc


class DiagnosticErrorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    error_id: uuid.UUID = Field(validation_alias="id")
    request_id: uuid.UUID
    code: str
    message: str
    operation: str
    details: dict[str, Any]
    exception_type: str | None
    created_at: datetime


class DiagnosticExplainRequest(BaseModel):
    model: str | None = Field(default=None, min_length=1, max_length=100)


class DiagnosticExplanationResponse(DiagnosticExplanation):
    error_id: uuid.UUID
    request_id: uuid.UUID
    model: str
    explained_at: datetime
