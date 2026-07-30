import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.course_sources.models import CourseSourceType, ExtractionStatus


class CourseSourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    course_id: uuid.UUID
    source_type: CourseSourceType
    display_name: str
    original_filename: str
    stored_filename: str
    mime_type: str
    file_size: int
    external_id: str | None
    extraction_status: ExtractionStatus
    extraction_error: str | None
    extracted_text_count: int
    created_at: datetime
    updated_at: datetime
