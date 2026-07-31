from __future__ import annotations

import re
from typing import Any

REDACTED = "[REDACTED]"
PRIVATE_PATH = "[PRIVATE_PATH]"
MAX_SAFE_STRING_LENGTH = 2_000
MAX_COLLECTION_ITEMS = 50

_SENSITIVE_KEY_PARTS = {
    "authorization",
    "cookie",
    "credential",
    "databaseurl",
    "dbpassword",
    "apikey",
    "password",
    "secret",
    "session",
    "token",
}
_VALUE_PATTERNS = (
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]+"),
    re.compile(r"(?i)\bsk-[A-Za-z0-9_-]{8,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(
        r"(?i)\b(password|secret|token|api[_-]?key|authorization|cookie)"
        r"\s*[:=]\s*[^\s,;]+"
    ),
    re.compile(r"(?i)\b(?:postgres(?:ql)?|mysql|redis)://[^\s]+"),
)
_PRIVATE_PATH_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_.-])(?:/home/[^/\s]+|/Users/[^/\s]+|/app)(?:/[^\s:,;]+)*"
)


def _normalized_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def is_sensitive_key(key: str) -> bool:
    normalized = _normalized_key(key)
    return any(part in normalized for part in _SENSITIVE_KEY_PARTS)


def redact_text(value: str, *, max_length: int = MAX_SAFE_STRING_LENGTH) -> str:
    safe = value
    for pattern in _VALUE_PATTERNS:
        safe = pattern.sub(REDACTED, safe)
    safe = _PRIVATE_PATH_PATTERN.sub(PRIVATE_PATH, safe)
    return safe[:max_length]


def redact(value: Any, *, key: str | None = None) -> Any:
    if key is not None and is_sensitive_key(key):
        return REDACTED
    if value is None or isinstance(value, bool | int | float):
        return value
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, dict):
        return {
            str(item_key)[:120]: redact(item_value, key=str(item_key))
            for item_key, item_value in list(value.items())[:MAX_COLLECTION_ITEMS]
        }
    if isinstance(value, list | tuple):
        return [redact(item) for item in value[:MAX_COLLECTION_ITEMS]]
    return redact_text(type(value).__name__)
