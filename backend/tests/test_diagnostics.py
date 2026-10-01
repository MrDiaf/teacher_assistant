import json
import uuid
from collections.abc import Iterator
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.codex_runtime.adapter import (
    CodexRuntimeResult,
    get_codex_adapter,
)
from app.diagnostics.models import DiagnosticAuditRecord, DiagnosticError
from app.diagnostics.redaction import REDACTED, redact
from app.diagnostics.service import DiagnosticService, record_diagnostic_error
from app.main import app


class FakeDiagnosticAdapter:
    def __init__(self) -> None:
        self.response = json.dumps(
            {
                "plain_explanation": "The course name did not pass validation.",
                "likely_cause": "The submitted name was blank.",
                "input_fixes": ["Enter a non-empty course name."],
                "application_improvements": [
                    "Keep the form submit button disabled for blank names."
                ],
                "retry_is_safe": True,
            }
        )
        self.calls: list[dict[str, Any]] = []

    async def answer(self, workspace, model=None) -> CodexRuntimeResult:
        self.calls.append(
            {
                "model": model,
                "root": workspace.root,
                "policy": (workspace.job_directory / "AGENT.md").read_text(),
                "error_context": json.loads(
                    (workspace.job_directory / "ERROR_CONTEXT.json").read_text()
                ),
                "schema": json.loads(
                    (workspace.job_directory / "OUTPUT_SCHEMA.json").read_text()
                ),
                "files": sorted(
                    str(path.relative_to(workspace.job_directory))
                    for path in workspace.job_directory.rglob("*")
                ),
            }
        )
        return CodexRuntimeResult(final_response=self.response)


@pytest.fixture
def fake_diagnostic_adapter() -> Iterator[FakeDiagnosticAdapter]:
    adapter = FakeDiagnosticAdapter()
    app.dependency_overrides[get_codex_adapter] = lambda: adapter
    try:
        yield adapter
    finally:
        app.dependency_overrides.pop(get_codex_adapter, None)


def test_redaction_removes_secrets_credentials_private_paths_and_sensitive_keys() -> None:
    safe = redact(
        {
            "authorization": "Bearer owner-token",
            "nested": {
                "api_key": "sk-owner-secret-key",
                "message": (
                    "password=hunter2 database=postgresql://owner:secret@db/app "
                    "failed in /home/owner/private/repository/app.py"
                ),
            },
            "public_code": "invalid_course_name",
        }
    )

    serialized = json.dumps(safe)
    assert safe["authorization"] == REDACTED
    assert safe["nested"]["api_key"] == REDACTED
    assert "hunter2" not in serialized
    assert "postgresql://" not in serialized
    assert "/home/owner" not in serialized
    assert safe["public_code"] == "invalid_course_name"


async def test_diagnostic_record_persists_only_redacted_context(
    client: AsyncClient,
    session: AsyncSession,
) -> None:
    report = await DiagnosticService(session).record_error(
        request_id=uuid.uuid4(),
        code="upload_failed",
        message="Upload failed with token=owner-private-token",
        operation="POST /api/v1/courses/{course_id}/sources",
        details={
            "file_type": "application/pdf",
            "file_size": 4096,
            "cookie": "owner-session-cookie",
            "trace": "/app/course_sources/service.py password=hunter2",
        },
        exception_type="ExtractionFailure",
    )

    response = await client.get(f"/api/v1/diagnostics/errors/{report.id}")

    assert response.status_code == 200, response.text
    body = response.json()
    serialized = json.dumps(body)
    assert body["code"] == "upload_failed"
    assert body["details"]["file_type"] == "application/pdf"
    assert body["details"]["file_size"] == 4096
    assert body["details"]["cookie"] == REDACTED
    assert "owner-private-token" not in serialized
    assert "hunter2" not in serialized
    assert "/app/" not in serialized


async def test_public_diagnostic_recorder_owns_its_transaction(
    client: AsyncClient,
) -> None:
    request_id = uuid.uuid4()
    report = await record_diagnostic_error(
        request_id=request_id,
        code="bounded_failure",
        message="The operation failed safely.",
        operation="test_operation",
        details={"authorization": "secret", "safe": "value"},
    )

    assert report.request_id == request_id
    assert report.code == "bounded_failure"
    stored = await client.get(f"/api/v1/diagnostics/errors/{report.id}")
    assert stored.status_code == 200
    assert stored.json()["details"] == {
        "authorization": REDACTED,
        "safe": "value",
    }


async def test_validation_error_can_be_explained_from_isolated_sanitized_context(
    client: AsyncClient,
    session: AsyncSession,
    fake_diagnostic_adapter: FakeDiagnosticAdapter,
) -> None:
    invalid = await client.post(
        "/api/v1/courses",
        json={
            "name": "",
            "course_code": "SEC101",
            "description": None,
            "term": None,
            "color": "#29584c",
            "password": "must-never-reach-diagnostics",
        },
    )

    assert invalid.status_code == 422, invalid.text
    error_body = invalid.json()
    assert error_body["code"] == "request_validation_error"
    assert uuid.UUID(error_body["error_id"])
    assert uuid.UUID(error_body["request_id"])
    assert error_body["details"]["field_errors"]
    assert "must-never-reach-diagnostics" not in invalid.text

    stored = await client.get(
        f"/api/v1/diagnostics/errors/{error_body['error_id']}"
    )
    assert stored.status_code == 200
    assert stored.json()["operation"] == "POST /api/v1/courses"

    explained = await client.post(
        f"/api/v1/diagnostics/errors/{error_body['error_id']}/explain",
        json={"model": "gpt-5.6-terra"},
    )

    assert explained.status_code == 200, explained.text
    explanation = explained.json()
    assert explanation["plain_explanation"].startswith("The course name")
    assert explanation["input_fixes"] == ["Enter a non-empty course name."]
    assert explanation["application_improvements"] == [
        "Keep the form submit button disabled for blank names."
    ]
    assert explanation["retry_is_safe"] is True
    assert explanation["model"] == "gpt-5.6-terra"

    call = fake_diagnostic_adapter.calls[0]
    context = json.dumps(call["error_context"])
    assert call["model"] == "gpt-5.6-terra"
    assert "must-never-reach-diagnostics" not in context
    assert "calendar" not in call["files"]
    assert "COURSES.json" not in call["files"]
    assert "CALENDARS.json" not in call["files"]
    assert "ERROR_CONTEXT.json" in call["files"]
    assert "Never access or edit application source code" in call["policy"]
    assert not call["root"].exists()

    error = await session.get(
        DiagnosticError,
        uuid.UUID(error_body["error_id"]),
    )
    assert error is not None
    assert error.explanation == {
        "plain_explanation": "The course name did not pass validation.",
        "likely_cause": "The submitted name was blank.",
        "input_fixes": ["Enter a non-empty course name."],
        "application_improvements": [
            "Keep the form submit button disabled for blank names."
        ],
        "retry_is_safe": True,
    }
    actions = list(
        await session.scalars(
            select(DiagnosticAuditRecord.action)
            .where(
                DiagnosticAuditRecord.error_id
                == uuid.UUID(error_body["error_id"])
            )
            .order_by(DiagnosticAuditRecord.created_at)
        )
    )
    assert actions == [
        "recorded",
        "explanation_requested",
        "explanation_completed",
    ]
