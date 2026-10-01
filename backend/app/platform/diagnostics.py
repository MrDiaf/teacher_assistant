"""Stable Platform imports for bounded, sanitized diagnostic interfaces.

This module exposes schemas, redaction, explanation behavior, and an
independently transacted recording function without leaking persistence details.
"""

from app.diagnostics.redaction import (
    MAX_COLLECTION_ITEMS,
    MAX_SAFE_STRING_LENGTH,
    PRIVATE_PATH,
    REDACTED,
    is_sensitive_key,
    redact,
    redact_text,
)
from app.diagnostics.schemas import (
    DIAGNOSTIC_OUTPUT_SCHEMA,
    DiagnosticErrorResponse,
    DiagnosticExplainRequest,
    DiagnosticExplanation,
    DiagnosticExplanationResponse,
    parse_diagnostic_explanation,
)
from app.diagnostics.service import (
    DiagnosticRecord,
    DiagnosticService,
    record_diagnostic_error,
)

__all__ = [
    "DIAGNOSTIC_OUTPUT_SCHEMA",
    "MAX_COLLECTION_ITEMS",
    "MAX_SAFE_STRING_LENGTH",
    "PRIVATE_PATH",
    "REDACTED",
    "DiagnosticErrorResponse",
    "DiagnosticExplainRequest",
    "DiagnosticExplanation",
    "DiagnosticExplanationResponse",
    "DiagnosticRecord",
    "DiagnosticService",
    "is_sensitive_key",
    "parse_diagnostic_explanation",
    "redact",
    "redact_text",
    "record_diagnostic_error",
]
