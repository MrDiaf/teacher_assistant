import uuid

from pydantic import BaseModel, ConfigDict


class CourseCalendarLinkCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    calendar_id: uuid.UUID
