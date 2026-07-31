from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.service import AiModelRegistry
from app.codex_runtime.adapter import CodexAdapter
from app.codex_runtime.workspace import create_diagnostic_workspace
from app.diagnostics.models import DiagnosticError
from app.diagnostics.redaction import redact, redact_text
from app.diagnostics.repository import DiagnosticRepository
from app.diagnostics.schemas import (
    DIAGNOSTIC_OUTPUT_SCHEMA,
    DiagnosticExplanation,
    parse_diagnostic_explanation,
)


class DiagnosticService:
    def __init__(
        self,
        session: AsyncSession,
        adapter: CodexAdapter | None = None,
    ) -> None:
        self.session = session
        self.adapter = adapter
        self.repository = DiagnosticRepository(session)
        self.models = AiModelRegistry()

    async def record_error(
        self,
        *,
        request_id: uuid.UUID,
        code: str,
        message: str,
        operation: str,
        details: dict[str, Any],
        exception_type: str | None = None,
    ) -> DiagnosticError:
        error = await self.repository.create_error(
            request_id=request_id,
            code=redact_text(code)[:80],
            message=redact_text(message),
            operation=redact_text(operation)[:240],
            details=redact(details),
            exception_type=(redact_text(exception_type)[:120] if exception_type else None),
        )
        await self.repository.add_audit(
            error.id,
            "recorded",
            {"detail_fields": sorted(error.details)},
        )
        await self.session.commit()
        await self.session.refresh(error)
        return error

    async def get_error(self, error_id: uuid.UUID) -> DiagnosticError:
        return await self.repository.get(error_id)

    async def explain(
        self,
        error_id: uuid.UUID,
        *,
        model: str | None = None,
    ) -> tuple[DiagnosticError, DiagnosticExplanation]:
        if self.adapter is None:
            raise RuntimeError("A Codex adapter is required for diagnostic explanations.")
        selected_model = self.models.resolve(model)
        error = await self.repository.get(error_id, for_update=True)
        await self.repository.add_audit(
            error.id,
            "explanation_requested",
            {"model": selected_model},
        )
        await self.session.commit()

        error_context = {
            "error_id": str(error.id),
            "request_id": str(error.request_id),
            "code": error.code,
            "message": error.message,
            "operation": error.operation,
            "details": error.details,
            "exception_type": error.exception_type,
            "constraints": {
                "explain_only_supplied_sanitized_context": True,
                "do_not_request_or_infer_secrets": True,
                "do_not_edit_application_source": True,
                "separate_owner_input_fixes_from_application_improvements": True,
            },
        }
        try:
            with create_diagnostic_workspace(
                error_context=error_context,
                output_schema=DIAGNOSTIC_OUTPUT_SCHEMA,
            ) as workspace:
                runtime_result = await self.adapter.answer(workspace, model=selected_model)
                explanation = parse_diagnostic_explanation(runtime_result.final_response)
        except Exception:
            await self.session.rollback()
            error = await self.repository.get(error_id, for_update=True)
            await self.repository.add_audit(
                error.id,
                "explanation_failed",
                {"model": selected_model},
            )
            await self.session.commit()
            raise

        explained_at = datetime.now(UTC)
        error = await self.repository.get(error_id, for_update=True)
        error.explanation = explanation.model_dump(mode="json")
        error.explanation_model = selected_model
        error.explained_at = explained_at
        await self.repository.add_audit(
            error.id,
            "explanation_completed",
            {
                "model": selected_model,
                "input_fix_count": len(explanation.input_fixes),
                "application_improvement_count": len(explanation.application_improvements),
            },
        )
        await self.session.commit()
        await self.session.refresh(error)
        return error, explanation
