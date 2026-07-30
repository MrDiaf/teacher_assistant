import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.notes.summary_models import NoteSummary, NoteSummaryStatus
from app.notes.summary_validation import StructuredNoteSummary


class NoteSummaryCreate(BaseModel):
    model: str | None = Field(default=None, min_length=1, max_length=100)


class NoteSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    note_id: uuid.UUID
    model: str
    status: NoteSummaryStatus
    summary_json: StructuredNoteSummary | None
    note_content_hash: str
    slide_content_hash: str
    is_stale: bool
    safe_error: str | None
    safe_error_code: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_summary(
        cls,
        summary: NoteSummary,
        *,
        is_stale: bool,
    ) -> "NoteSummaryResponse":
        return cls(
            id=summary.id,
            note_id=summary.note_id,
            model=summary.model,
            status=summary.status,
            summary_json=summary.summary_json,
            note_content_hash=summary.note_content_hash,
            slide_content_hash=summary.slide_content_hash,
            is_stale=is_stale,
            safe_error=summary.safe_error,
            safe_error_code=summary.safe_error_code,
            created_at=summary.created_at,
            updated_at=summary.updated_at,
        )
