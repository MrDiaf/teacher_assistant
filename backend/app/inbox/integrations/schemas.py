from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator

from app.inbox.integrations.models import IntegrationStatus, MailTlsMode


class MailConnectionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    host: str = Field(min_length=1, max_length=253)
    port: int = Field(ge=1, le=65535)
    tls_mode: MailTlsMode
    mailbox: str = Field(default="INBOX", min_length=1, max_length=255)
    username: str = Field(min_length=1, max_length=320)
    password: SecretStr = Field(min_length=1, max_length=4096)

    @field_validator("host", "mailbox", "username")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized or any(ord(character) < 32 for character in normalized):
            raise ValueError("The value contains invalid characters.")
        return normalized


class MailConnectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    connected: bool
    status: IntegrationStatus | None = None
    host: str | None = None
    port: int | None = None
    tls_mode: MailTlsMode | None = None
    mailbox: str | None = None
    username: str | None = None
    last_checked_at: datetime | None = None
    last_success_at: datetime | None = None
    next_check_at: datetime | None = None
    safe_error_code: str | None = None
    safe_error: str | None = None
    source_warning: str | None = None
    quarantined_count: int = 0


class MailCheckResponse(BaseModel):
    imported_count: int
    skipped_count: int
    quarantined_count: int
    status: MailConnectionResponse
