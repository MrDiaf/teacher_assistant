from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from app.core.errors import InvalidAssistantResponseError


class ReadOnlyAssistantAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1, max_length=8000)
    proposal: None

    @field_validator("message")
    @classmethod
    def normalize_message(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("The assistant message cannot be blank.")
        return normalized


READ_ONLY_OUTPUT_SCHEMA = ReadOnlyAssistantAnswer.model_json_schema()


def parse_read_only_answer(raw_response: str | None) -> ReadOnlyAssistantAnswer:
    if raw_response is None:
        raise InvalidAssistantResponseError()
    try:
        return ReadOnlyAssistantAnswer.model_validate_json(raw_response)
    except ValidationError as exc:
        raise InvalidAssistantResponseError() from exc
