from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.inbox.models import MailAddressKind


class MailAddressResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    kind: MailAddressKind
    display_name: str | None
    address: str
    position: int


class MailAttachmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    original_filename: str
    mime_type: str
    file_size: int
    status: str
    omission_reason: str | None


class MailMessageListResponse(BaseModel):
    id: uuid.UUID
    subject: str
    sender_name: str | None
    sender_address: str
    recipients: list[str]
    source_date: datetime | None
    ingested_at: datetime
    attachment_count: int
    omitted_attachment_count: int
    is_read: bool
    is_archived: bool
    forwarded_unverified: bool
    source_label: str = "Mail"


class MailMessageResponse(MailMessageListResponse):
    message_id: str | None
    in_reply_to: str | None
    thread_references: list[str]
    body_text: str
    body_html: str | None
    addresses: list[MailAddressResponse]
    attachments: list[MailAttachmentResponse]


class MailStateUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_read: bool | None = None
    is_archived: bool | None = None
