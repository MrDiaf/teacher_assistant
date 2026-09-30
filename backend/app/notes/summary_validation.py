from __future__ import annotations

import json
import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from app.courses.errors import InvalidNoteSummaryResponseError


class SummarySourceReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    note_id: uuid.UUID | None
    source_id: uuid.UUID | None
    slide: int | None = Field(ge=1)

    @model_validator(mode="after")
    def validate_reference_shape(self) -> SummarySourceReference:
        is_note = self.note_id is not None
        is_slide = self.source_id is not None and self.slide is not None
        if is_note == is_slide:
            raise ValueError(
                "A source reference must identify either one note or one source slide."
            )
        if is_note and (self.source_id is not None or self.slide is not None):
            raise ValueError("A note reference cannot include slide fields.")
        if not is_note and self.note_id is not None:
            raise ValueError("A slide reference cannot include a note ID.")
        return self


class GeneratedSummaryBullet(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=1000)
    origin: Literal["note", "slide", "mixed"]
    source_references: list[SummarySourceReference] = Field(
        min_length=1,
        max_length=20,
    )


class GeneratedStructuredNoteSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bullets: list[GeneratedSummaryBullet] = Field(min_length=1, max_length=20)


class SummaryBullet(GeneratedSummaryBullet):
    id: uuid.UUID


class StructuredNoteSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # A completed summary may be empty after the owner removes its final bullet.
    bullets: list[SummaryBullet] = Field(max_length=20)


SUMMARY_OUTPUT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "bullets": {
            "type": "array",
            "minItems": 1,
            "maxItems": 20,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "text": {"type": "string", "minLength": 1, "maxLength": 1000},
                    "origin": {
                        "type": "string",
                        "enum": ["note", "slide", "mixed"],
                    },
                    "source_references": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": 20,
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "note_id": {
                                    "type": ["string", "null"],
                                    "format": "uuid",
                                },
                                "source_id": {
                                    "type": ["string", "null"],
                                    "format": "uuid",
                                },
                                "slide": {
                                    "type": ["integer", "null"],
                                    "minimum": 1,
                                },
                            },
                            "required": ["note_id", "source_id", "slide"],
                        },
                    },
                },
                "required": ["text", "origin", "source_references"],
            },
        }
    },
    "required": ["bullets"],
}


def parse_and_validate_summary(
    raw_response: str | None,
    *,
    note_id: uuid.UUID,
    note_available: bool,
    available_slides: set[tuple[uuid.UUID, int]],
) -> GeneratedStructuredNoteSummary:
    if not raw_response:
        raise InvalidNoteSummaryResponseError()
    try:
        payload = json.loads(raw_response)
        summary = GeneratedStructuredNoteSummary.model_validate(payload)
    except (json.JSONDecodeError, ValidationError, TypeError) as exc:
        raise InvalidNoteSummaryResponseError() from exc

    for bullet in summary.bullets:
        has_note = False
        has_slide = False
        for reference in bullet.source_references:
            if reference.note_id is not None:
                if not note_available or reference.note_id != note_id:
                    raise InvalidNoteSummaryResponseError()
                has_note = True
            else:
                source_slide = (reference.source_id, reference.slide)
                if source_slide not in available_slides:
                    raise InvalidNoteSummaryResponseError()
                has_slide = True

        expected = {
            "note": (True, False),
            "slide": (False, True),
            "mixed": (True, True),
        }[bullet.origin]
        if (has_note, has_slide) != expected:
            raise InvalidNoteSummaryResponseError()
    return summary


def assign_summary_bullet_ids(
    summary: GeneratedStructuredNoteSummary,
) -> StructuredNoteSummary:
    """Assign server-owned identities only after Codex output was validated."""
    return StructuredNoteSummary(
        bullets=[
            SummaryBullet(id=uuid.uuid4(), **bullet.model_dump(mode="python"))
            for bullet in summary.bullets
        ]
    )


def normalize_stored_summary(
    payload: object,
    *,
    note_id: uuid.UUID,
) -> tuple[StructuredNoteSummary, bool]:
    """Validate persisted data and compatibly add IDs to legacy bullets."""
    if not isinstance(payload, dict) or set(payload) != {"bullets"}:
        raise InvalidNoteSummaryResponseError()
    raw_bullets = payload.get("bullets")
    if not isinstance(raw_bullets, list) or len(raw_bullets) > 20:
        raise InvalidNoteSummaryResponseError()

    changed = False
    bullets: list[SummaryBullet] = []
    try:
        for raw_bullet in raw_bullets:
            if not isinstance(raw_bullet, dict):
                raise InvalidNoteSummaryResponseError()
            bullet_payload = dict(raw_bullet)
            raw_id = bullet_payload.pop("id", None)
            generated = GeneratedSummaryBullet.model_validate(bullet_payload)
            if raw_id is None:
                bullet_id = uuid.uuid4()
                changed = True
            else:
                bullet_id = uuid.UUID(str(raw_id))
            bullets.append(
                SummaryBullet(
                    id=bullet_id,
                    **generated.model_dump(mode="python"),
                )
            )
    except (ValidationError, TypeError, ValueError) as exc:
        raise InvalidNoteSummaryResponseError() from exc

    summary = StructuredNoteSummary(bullets=bullets)
    _validate_stored_provenance(summary, note_id=note_id)
    return summary, changed


def _validate_stored_provenance(
    summary: StructuredNoteSummary,
    *,
    note_id: uuid.UUID,
) -> None:
    seen_ids: set[uuid.UUID] = set()
    for bullet in summary.bullets:
        if bullet.id in seen_ids:
            raise InvalidNoteSummaryResponseError()
        seen_ids.add(bullet.id)
        has_note = False
        has_slide = False
        for reference in bullet.source_references:
            if reference.note_id is not None:
                if reference.note_id != note_id:
                    raise InvalidNoteSummaryResponseError()
                has_note = True
            else:
                has_slide = True
        expected = {
            "note": (True, False),
            "slide": (False, True),
            "mixed": (True, True),
        }[bullet.origin]
        if (has_note, has_slide) != expected:
            raise InvalidNoteSummaryResponseError()
