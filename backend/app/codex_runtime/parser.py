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
        raise InvalidAssistantResponseError(
            "The model returned no final response.",
            validation_stage="response_parsing",
        )
    try:
        return ReadOnlyAssistantAnswer.model_validate_json(raw_response)
    except ValidationError as exc:
        errors = [
            {
                "field": ".".join(str(item) for item in entry.get("loc", ()))
                or "response",
                "message": str(entry.get("msg", "Invalid value."))[:500],
                "type": str(entry.get("type", "validation_error"))[:120],
            }
            for entry in exc.errors()
        ][:20]
        raise InvalidAssistantResponseError(
            "The response did not match the required read-only answer schema.",
            validation_stage="response_schema",
            validation_errors=errors,
        ) from exc
