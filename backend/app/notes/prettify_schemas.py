from pydantic import BaseModel, ConfigDict, Field


class NotePrettifyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    body: str = Field(max_length=100_000)
    model: str | None = Field(default=None, min_length=1, max_length=100)


class NotePrettifyResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    proposed_body: str
    has_changes: bool
    message: str
    model: str
