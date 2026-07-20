from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.assistant.models import AssistantJobStatus, AssistantProposal, AssistantProposalStatus
from app.assistant.proposal_repository import ProposalRepository
from app.assistant.proposals import (
    CreateCalendarAction,
    CreateEventAction,
    DeleteEventAction,
    ProposalAction,
    UpdateCalendarAction,
    UpdateEventAction,
)
from app.assistant.repository import AssistantRepository
from app.assistant.validation import ProposalValidator
from app.calendar.models import CalendarSourceType
from app.calendar.repository import CalendarRepository, EventRepository
from app.calendar.schemas import CalendarResponse, EventResponse
from app.calendar.service import CalendarService
from app.core.errors import ApplicationError, AssistantProposalStateError

logger = logging.getLogger(__name__)


class ProposalService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.proposals = ProposalRepository(session)
        self.assistant = AssistantRepository(session)
        self.calendar_service = CalendarService(session)
        self.validator = ProposalValidator(CalendarRepository(session), EventRepository(session))

    async def get(self, proposal_id: uuid.UUID) -> AssistantProposal:
        proposal = await self.proposals.get(proposal_id)
        if await self._expire_if_needed(proposal):
            return await self.proposals.get(proposal_id)
        return proposal

    async def list_audit(self, *, limit: int = 50) -> list[AssistantProposal]:
        return await self.proposals.list_recent(limit=limit)

    async def confirm(self, proposal_id: uuid.UUID) -> AssistantProposal:
        proposal = await self.proposals.get(proposal_id, for_update=True)
        if proposal.status == AssistantProposalStatus.COMPLETED:
            return proposal
        if proposal.status == AssistantProposalStatus.FAILED:
            return proposal
        if await self._expire_if_needed(proposal):
            return await self.proposals.get(proposal_id)
        if proposal.status != AssistantProposalStatus.AWAITING_CONFIRMATION:
            raise AssistantProposalStateError()

        now = datetime.now(UTC)
        try:
            actions = await self.validator.revalidate(proposal)
            proposal.status = AssistantProposalStatus.CONFIRMED
            proposal.confirmed_at = now
            for record in proposal.action_records:
                record.confirmed_at = now
            await self.session.flush()

            proposal.status = AssistantProposalStatus.EXECUTING
            results: list[dict[str, Any]] = []
            for action, record in zip(actions, proposal.action_records, strict=True):
                action_result = await self._execute_action(action)
                record.executed_at = now
                record.result = action_result
                results.append(
                    {
                        "position": record.position,
                        "operation": record.operation,
                        "status": "completed",
                        "result": action_result,
                    }
                )

            proposal.status = AssistantProposalStatus.COMPLETED
            proposal.executed_at = now
            proposal.result = {"actions": results}
            proposal.safe_error = None
            await self.assistant.update_job(
                proposal.job_id,
                {
                    "status": AssistantJobStatus.COMPLETED,
                    "safe_error": None,
                    "safe_error_code": None,
                },
            )
            await self.session.commit()
            return await self.proposals.get(proposal.id)
        except ApplicationError as exc:
            await self.session.rollback()
            return await self._record_failed_execution(
                proposal_id,
                exc.message,
                error_code=exc.code,
                confirmed_at=now,
            )
        except Exception as exc:
            await self.session.rollback()
            logger.error(
                "Assistant proposal execution failed: proposal=%s error_type=%s",
                proposal_id,
                type(exc).__name__,
            )
            return await self._record_failed_execution(
                proposal_id,
                "The proposal could not be executed safely. No calendar data changed.",
                error_code="proposal_execution_failed",
                confirmed_at=now,
            )

    async def reject(self, proposal_id: uuid.UUID) -> AssistantProposal:
        proposal = await self.proposals.get(proposal_id, for_update=True)
        if proposal.status == AssistantProposalStatus.REJECTED:
            return proposal
        if await self._expire_if_needed(proposal):
            return await self.proposals.get(proposal_id)
        if proposal.status != AssistantProposalStatus.AWAITING_CONFIRMATION:
            raise AssistantProposalStateError()
        now = datetime.now(UTC)
        proposal.status = AssistantProposalStatus.REJECTED
        proposal.rejected_at = now
        proposal.result = {"status": "rejected_by_owner"}
        for record in proposal.action_records:
            record.result = {"status": "rejected_by_owner"}
        await self.assistant.update_job(
            proposal.job_id,
            {
                "status": AssistantJobStatus.COMPLETED,
                "safe_error": None,
                "safe_error_code": None,
            },
        )
        await self.session.commit()
        return await self.proposals.get(proposal.id)

    async def _execute_action(self, action: ProposalAction) -> dict[str, Any]:
        if isinstance(action, CreateCalendarAction):
            calendar = await self.calendar_service.create_calendar(
                {
                    "name": action.name,
                    "description": action.description,
                    "color": action.color,
                    "is_visible": True,
                    "is_read_only": False,
                    "source_type": CalendarSourceType.LOCAL,
                },
                commit=False,
            )
            return {"calendar": CalendarResponse.model_validate(calendar).model_dump(mode="json")}

        if isinstance(action, UpdateCalendarAction):
            calendar = await self.calendar_service.update_calendar(
                action.calendar_id,
                action.changes.change_values(),
                commit=False,
            )
            return {"calendar": CalendarResponse.model_validate(calendar).model_dump(mode="json")}

        if isinstance(action, CreateEventAction):
            event = await self.calendar_service.create_event(
                {
                    "calendar_id": action.calendar_id,
                    **action.event.model_dump(),
                },
                commit=False,
            )
            return {"event": EventResponse.model_validate(event).model_dump(mode="json")}

        if isinstance(action, UpdateEventAction):
            changes = action.changes.change_values()
            if action.recurrence_scope == "occurrence":
                event = await self.calendar_service.update_event_occurrence(
                    action.event_id,
                    action.occurrence_start_at,
                    changes,
                    commit=False,
                )
            elif action.recurrence_scope == "series":
                event = await self.calendar_service.update_event_series(
                    action.event_id, changes, commit=False
                )
            else:
                event = await self.calendar_service.update_event(
                    action.event_id, changes, commit=False
                )
            return {"event": EventResponse.model_validate(event).model_dump(mode="json")}

        if isinstance(action, DeleteEventAction):
            if action.recurrence_scope == "occurrence":
                await self.calendar_service.delete_event_occurrence(
                    action.event_id,
                    action.occurrence_start_at,
                    commit=False,
                )
            elif action.recurrence_scope == "series":
                await self.calendar_service.delete_event_series(action.event_id, commit=False)
            else:
                await self.calendar_service.delete_event(action.event_id, commit=False)
            return {"event_id": str(action.event_id), "deleted": True}

        raise AssistantProposalStateError("The proposal contains an unknown action.")

    async def _record_failed_execution(
        self,
        proposal_id: uuid.UUID,
        safe_error: str,
        *,
        error_code: str,
        confirmed_at: datetime,
    ) -> AssistantProposal:
        proposal = await self.proposals.get(proposal_id, for_update=True)
        proposal.status = AssistantProposalStatus.FAILED
        proposal.confirmed_at = confirmed_at
        proposal.safe_error = safe_error[:500]
        proposal.result = {
            "error_code": error_code[:80],
            "actions": [
                {
                    "position": record.position,
                    "operation": record.operation,
                    "status": "failed",
                    "error_code": error_code[:80],
                    "error": safe_error[:500],
                }
                for record in proposal.action_records
            ]
        }
        for record in proposal.action_records:
            record.confirmed_at = confirmed_at
            record.safe_error = safe_error[:500]
            record.result = {
                "status": "failed",
                "error_code": error_code[:80],
            }
        await self.assistant.update_job(
            proposal.job_id,
            {
                "status": AssistantJobStatus.COMPLETED,
                "safe_error": None,
                "safe_error_code": None,
            },
        )
        await self.session.commit()
        return await self.proposals.get(proposal.id)

    async def _expire_if_needed(self, proposal: AssistantProposal) -> bool:
        if (
            proposal.status == AssistantProposalStatus.AWAITING_CONFIRMATION
            and proposal.expires_at <= datetime.now(UTC)
        ):
            proposal.status = AssistantProposalStatus.EXPIRED
            proposal.safe_error = (
                "This proposal expired before confirmation. Ask the assistant for a new one."
            )
            await self.assistant.update_job(
                proposal.job_id,
                {
                    "status": AssistantJobStatus.COMPLETED,
                    "safe_error": None,
                    "safe_error_code": None,
                },
            )
            await self.session.commit()
            return True
        return False
