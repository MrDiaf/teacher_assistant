from __future__ import annotations

import hashlib
import html
import re
from datetime import UTC
from email import policy
from email.message import Message
from email.parser import BytesParser
from email.utils import getaddresses, parsedate_to_datetime
from html.parser import HTMLParser
from urllib.parse import urlsplit

from app.inbox.models import MailAddressKind
from app.integrations.mail.schemas import (
    MailParseError,
    ParsedAddress,
    ParsedAttachment,
    ParsedMail,
)

MAX_PARTS = 100
MAX_MIME_DEPTH = 20
MAX_BODY_CHARS = 200_000
MAX_HEADERS = 200
SAFE_TAGS = {
    "p",
    "br",
    "strong",
    "b",
    "em",
    "i",
    "blockquote",
    "ul",
    "ol",
    "li",
    "pre",
    "code",
    "a",
}
VOID_TAGS = {"br"}
BLOCKED_CONTENT_TAGS = {"script", "style", "svg", "form", "iframe", "object", "embed", "template"}


def _safe_href(value: str) -> str | None:
    candidate = value.strip()
    parsed = urlsplit(candidate)
    if parsed.scheme.lower() in {"http", "https", "mailto"}:
        return candidate
    return None


class PassiveHtmlSanitizer(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.output: list[str] = []
        self.blocked_depth = 0
        self.open_tags: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in BLOCKED_CONTENT_TAGS:
            self.blocked_depth += 1
            return
        if self.blocked_depth or tag not in SAFE_TAGS:
            return
        if tag == "a":
            href = next((value for name, value in attrs if name.lower() == "href"), None)
            safe = _safe_href(href or "")
            if safe:
                self.output.append(
                    f'<a href="{html.escape(safe, quote=True)}" '
                    'rel="noreferrer noopener" target="_blank">'
                )
                self.open_tags.append("a")
            return
        self.output.append(f"<{tag}>")
        if tag not in VOID_TAGS:
            self.open_tags.append(tag)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in BLOCKED_CONTENT_TAGS:
            if self.blocked_depth:
                self.blocked_depth -= 1
            return
        if self.blocked_depth or tag not in self.open_tags:
            return
        while self.open_tags:
            current = self.open_tags.pop()
            self.output.append(f"</{current}>")
            if current == tag:
                break

    def handle_data(self, data: str) -> None:
        if not self.blocked_depth:
            self.output.append(html.escape(data))

    def close(self) -> None:
        super().close()
        while self.open_tags:
            self.output.append(f"</{self.open_tags.pop()}>")


def sanitize_html(value: str) -> str:
    sanitizer = PassiveHtmlSanitizer()
    sanitizer.feed(value[:MAX_BODY_CHARS])
    sanitizer.close()
    return "".join(sanitizer.output)


def html_to_text(value: str) -> str:
    plain = re.sub(r"<[^>]*>", " ", sanitize_html(value))
    return re.sub(r"[ \t]+", " ", html.unescape(plain)).strip()[:MAX_BODY_CHARS]


def _decode_text(part: Message) -> str:
    try:
        content = part.get_content()
    except (LookupError, UnicodeError, ValueError) as exc:
        raise MailParseError(
            "invalid_charset", "A message text part could not be decoded."
        ) from exc
    if not isinstance(content, str):
        raise MailParseError("invalid_text_part", "A message text part was invalid.")
    return content.replace("\x00", "")[:MAX_BODY_CHARS]


def _depth(message: Message, current: int = 0) -> int:
    if current > MAX_MIME_DEPTH:
        return current
    payload = message.get_payload()
    if not isinstance(payload, list) or not payload:
        return current
    return max(_depth(part, current + 1) for part in payload)


def _header_text(message: Message, name: str, limit: int = 998) -> str | None:
    value = message.get(name)
    if value is None:
        return None
    return str(value).replace("\r", " ").replace("\n", " ").strip()[:limit] or None


def _addresses(message: Message) -> list[ParsedAddress]:
    result: list[ParsedAddress] = []
    mapping = (
        ("from", MailAddressKind.FROM),
        ("reply-to", MailAddressKind.REPLY_TO),
        ("to", MailAddressKind.TO),
        ("cc", MailAddressKind.CC),
    )
    for header, kind in mapping:
        values = message.get_all(header, [])[:50]
        for position, (name, address) in enumerate(getaddresses([str(value) for value in values])):
            normalized = address.strip()[:320]
            if normalized:
                result.append(
                    ParsedAddress(
                        kind=kind,
                        display_name=name.strip()[:320] or None,
                        address=normalized,
                        position=position,
                    )
                )
    if not any(item.kind == MailAddressKind.FROM for item in result):
        result.append(
            ParsedAddress(
                kind=MailAddressKind.FROM,
                display_name=None,
                address="Unknown sender",
                position=0,
            )
        )
    return result


def parse_mail(
    raw: bytes,
    *,
    maximum_message_bytes: int,
    maximum_attachment_bytes: int,
) -> ParsedMail:
    if not raw or len(raw) > maximum_message_bytes:
        raise MailParseError("message_too_large", "A message exceeded the configured size limit.")
    try:
        message = BytesParser(policy=policy.default).parsebytes(raw)
    except Exception as exc:
        raise MailParseError("malformed_message", "A message could not be parsed safely.") from exc
    if len(message.items()) > MAX_HEADERS:
        raise MailParseError("too_many_headers", "A message contained too many headers.")
    parts = list(message.walk())
    if len(parts) > MAX_PARTS or _depth(message) > MAX_MIME_DEPTH:
        raise MailParseError("mime_limits_exceeded", "A message exceeded safe MIME limits.")

    plain_parts: list[str] = []
    html_parts: list[str] = []
    attachments: list[ParsedAttachment] = []
    total_attachment_bytes = 0
    for part in parts:
        if part.is_multipart():
            continue
        disposition = part.get_content_disposition()
        filename = part.get_filename()
        mime_type = part.get_content_type()[:255]
        if disposition == "attachment" or filename:
            safe_name = "".join(
                character
                for character in str(filename or "attachment")
                if ord(character) >= 32 and character not in {"/", "\\"}
            ).strip()[:255]
            safe_name = safe_name or "attachment"
            try:
                content = part.get_payload(decode=True) or b""
            except Exception:
                content = b""
            total_attachment_bytes += len(content)
            reason = None
            accepted: bytes | None = content
            if not content:
                reason, accepted = "The attachment was empty or malformed.", None
            elif len(content) > maximum_attachment_bytes:
                reason, accepted = "The attachment exceeded the configured size limit.", None
            elif total_attachment_bytes > maximum_message_bytes:
                reason, accepted = "Message attachments exceeded the configured total limit.", None
            attachments.append(
                ParsedAttachment(
                    original_filename=safe_name,
                    mime_type=mime_type,
                    content=accepted,
                    omission_reason=reason,
                )
            )
            continue
        if mime_type == "text/plain":
            plain_parts.append(_decode_text(part))
        elif mime_type == "text/html":
            html_parts.append(_decode_text(part))

    sanitized_html = sanitize_html("\n".join(html_parts)) if html_parts else None
    body_text = "\n".join(plain_parts).strip()[:MAX_BODY_CHARS]
    if not body_text and sanitized_html:
        body_text = html_to_text(sanitized_html)
    source_date = None
    date_header = _header_text(message, "date")
    if date_header:
        try:
            source_date = parsedate_to_datetime(date_header)
            if source_date.tzinfo is None:
                source_date = source_date.replace(tzinfo=UTC)
            else:
                source_date = source_date.astimezone(UTC)
        except (TypeError, ValueError, OverflowError):
            source_date = None
    references = (_header_text(message, "references", 8000) or "").split()[:100]
    subject = _header_text(message, "subject") or "(No subject)"
    return ParsedMail(
        subject=subject,
        message_id=_header_text(message, "message-id"),
        in_reply_to=_header_text(message, "in-reply-to"),
        thread_references=references,
        source_date=source_date,
        body_text=body_text,
        body_html=sanitized_html if not plain_parts else None,
        addresses=_addresses(message),
        attachments=attachments,
        content_hash=hashlib.sha256(raw).hexdigest(),
        forwarded_unverified=True,
    )
