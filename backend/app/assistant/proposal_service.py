from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.assistant.errors import AssistantProposalStateError
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
from app.calendar.public import (
    AssistantCalendarCreate,
    AssistantCalendarUpdate,
    AssistantEventCreate,
    AssistantEventUpdate,
    assistant_calendar_port,
)
from app.core.errors import ApplicationError

logger = logging.getLogger(__name__)


class ProposalService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.proposals = ProposalRepository(session)
        self.assistant = AssistantRepository(session)
        self.calendar = assistant_calendar_port(session)
        self.validator = ProposalValidator(self.calendar)

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
            await self._sync_job_status(proposal.job_id)
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
        await self._sync_job_status(proposal.job_id)
        await self.session.commit()
        return await self.proposals.get(proposal.id)

    async def reject_plan(self, proposal_id: uuid.UUID) -> AssistantProposal:
        proposal = await self.proposals.get(proposal_id, for_update=True)
        if await self._expire_if_needed(proposal):
            return await self.proposals.get(proposal_id)
        if proposal.status != AssistantProposalStatus.AWAITING_CONFIRMATION:
            raise AssistantProposalStateError()

        now = datetime.now(UTC)
        siblings = await self.proposals.list_for_job(proposal.job_id, for_update=True)
        for sibling in siblings:
            if sibling.status != AssistantProposalStatus.AWAITING_CONFIRMATION:
                continue
            sibling.status = AssistantProposalStatus.REJECTED
            sibling.rejected_at = now
            sibling.result = {"status": "rejected_for_plan_revision"}
            for record in sibling.action_records:
                record.result = {"status": "rejected_for_plan_revision"}
        await self._sync_job_status(proposal.job_id)
        await self.session.commit()
        return await self.proposals.get(proposal.id)

    async def _execute_action(self, action: ProposalAction) -> dict[str, Any]:
        if isinstance(action, CreateCalendarAction):
            calendar = await self.calendar.create_calendar(
                AssistantCalendarCreate(
                    name=action.name,
                    description=action.description,
                    color=action.color,
                )
            )
            return {"calendar": calendar.model_dump(mode="json")}

        if isinstance(action, UpdateCalendarAction):
            calendar = await self.calendar.update_calendar(
                action.calendar_id,
                AssistantCalendarUpdate.model_validate(action.changes.change_values()),
            )
            return {"calendar": calendar.model_dump(mode="json")}

        if isinstance(action, CreateEventAction):
            event = await self.calendar.create_event(
                AssistantEventCreate(
                    calendar_id=action.calendar_id,
                    **action.event.model_dump(),
                )
            )
            return {"event": event.model_dump(mode="json")}

        if isinstance(action, UpdateEventAction):
            changes = action.changes.change_values()
            event = await self.calendar.update_event(
                action.event_id,
                AssistantEventUpdate.model_validate(changes),
                recurrence_scope=action.recurrence_scope or "single",
                occurrence_start_at=action.occurrence_start_at,
            )
            return {"event": event.model_dump(mode="json")}

        if isinstance(action, DeleteEventAction):
            await self.calendar.delete_event(
                action.event_id,
                recurrence_scope=action.recurrence_scope or "single",
                occurrence_start_at=action.occurrence_start_at,
            )
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
        await self._sync_job_status(proposal.job_id)
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
            await self._sync_job_status(proposal.job_id)
            await self.session.commit()
            return True
        return False

    async def _sync_job_status(self, job_id: uuid.UUID) -> None:
        proposals = await self.proposals.list_for_job(job_id)
        has_open_batch = any(
            proposal.status
            in {
                AssistantProposalStatus.AWAITING_CONFIRMATION,
                AssistantProposalStatus.CONFIRMED,
                AssistantProposalStatus.EXECUTING,
            }
            for proposal in proposals
        )
        await self.assistant.update_job(
            job_id,
            {
                "status": (
                    AssistantJobStatus.AWAITING_CONFIRMATION
                    if has_open_batch
                    else AssistantJobStatus.COMPLETED
                ),
                "safe_error": None,
                "safe_error_code": None,
            },
        )
