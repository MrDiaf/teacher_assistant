"""Stable Platform imports for existing bounded diagnostic interfaces.

M21F owns separating their implementation from persistence details. This module
only publishes the already-enforced schemas, redaction, and service behavior.
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
from app.diagnostics.service import DiagnosticService

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
    "DiagnosticService",
    "is_sensitive_key",
    "parse_diagnostic_explanation",
    "redact",
    "redact_text",
]
