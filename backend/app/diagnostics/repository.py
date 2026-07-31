from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DiagnosticErrorNotFoundError
from app.diagnostics.models import DiagnosticAuditRecord, DiagnosticError


class DiagnosticRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_error(
        self,
        *,
        request_id: uuid.UUID,
        code: str,
        message: str,
        operation: str,
        details: dict[str, Any],
        exception_type: str | None,
    ) -> DiagnosticError:
        error = DiagnosticError(
            request_id=request_id,
            code=code,
            message=message,
            operation=operation,
            details=details,
            exception_type=exception_type,
        )
        self.session.add(error)
        await self.session.flush()
        return error

    async def get(self, error_id: uuid.UUID, *, for_update: bool = False) -> DiagnosticError:
        error = await self.session.get(
            DiagnosticError,
            error_id,
            with_for_update=for_update,
        )
        if error is None:
            raise DiagnosticErrorNotFoundError()
        return error

    async def add_audit(
        self,
        error_id: uuid.UUID,
        action: str,
        details: dict[str, Any] | None = None,
    ) -> DiagnosticAuditRecord:
        record = DiagnosticAuditRecord(
            error_id=error_id,
            action=action,
            details=details or {},
            created_at=datetime.now(UTC),
        )
        self.session.add(record)
        await self.session.flush()
        return record
