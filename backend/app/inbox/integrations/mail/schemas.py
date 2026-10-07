from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.inbox.integrations.models import MailTlsMode
from app.inbox.models import MailAddressKind


@dataclass(frozen=True)
class MailboxConfiguration:
    host: str
    port: int
    tls_mode: MailTlsMode
    mailbox: str
    username: str
    timeout_seconds: int
    maximum_message_bytes: int = 15 * 1024 * 1024
    maximum_messages_per_sync: int = 250


@dataclass(frozen=True)
class RemoteMail:
    uid: int
    raw: bytes


@dataclass(frozen=True)
class MailboxSnapshot:
    uid_validity: int
    messages: list[RemoteMail]


@dataclass(frozen=True)
class ParsedAddress:
    kind: MailAddressKind
    display_name: str | None
    address: str
    position: int


@dataclass(frozen=True)
class ParsedAttachment:
    original_filename: str
    mime_type: str
    content: bytes | None
    omission_reason: str | None


@dataclass(frozen=True)
class ParsedMail:
    subject: str
    message_id: str | None
    in_reply_to: str | None
    thread_references: list[str]
    source_date: datetime | None
    body_text: str
    body_html: str | None
    addresses: list[ParsedAddress]
    attachments: list[ParsedAttachment]
    content_hash: str
    forwarded_unverified: bool


class MailParseError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)
