from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.assistant.models import (
    AssistantProposal,
    AssistantProposalAction,
    AssistantProposalStatus,
)
from app.core.errors import AssistantProposalNotFoundError


class ProposalRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        job_id: uuid.UUID,
        conversation_id: uuid.UUID,
        summary: str,
        actions: list[dict[str, Any]],
        baselines: list[dict[str, Any]],
        review_items: list[dict[str, Any]],
        warnings: list[str],
        affected_events: int,
        expires_at: datetime,
        requested_at: datetime,
    ) -> AssistantProposal:
        action_records = [
            AssistantProposalAction(
                position=position,
                operation=action["operation"],
                target_calendar_id=self._uuid_or_none(action.get("calendar_id")),
                target_event_id=self._uuid_or_none(action.get("event_id")),
                requested_at=requested_at,
            )
            for position, action in enumerate(actions)
        ]
        proposal = AssistantProposal(
            job_id=job_id,
            conversation_id=conversation_id,
            status=AssistantProposalStatus.AWAITING_CONFIRMATION,
            summary=summary,
            actions=actions,
            baselines=baselines,
            review_items=review_items,
            warnings=warnings,
            affected_events=affected_events,
            expires_at=expires_at,
            action_records=action_records,
        )
        self.session.add(proposal)
        await self.session.flush()
        return proposal

    async def get(
        self, proposal_id: uuid.UUID, *, for_update: bool = False
    ) -> AssistantProposal:
        statement = (
            select(AssistantProposal)
            .where(AssistantProposal.id == proposal_id)
            .options(selectinload(AssistantProposal.action_records))
        )
        if for_update:
            statement = statement.with_for_update()
        proposal = await self.session.scalar(statement)
        if proposal is None:
            raise AssistantProposalNotFoundError()
        return proposal

    async def list_for_conversation(
        self, conversation_id: uuid.UUID
    ) -> list[AssistantProposal]:
        statement = (
            select(AssistantProposal)
            .where(AssistantProposal.conversation_id == conversation_id)
            .options(selectinload(AssistantProposal.action_records))
            .order_by(AssistantProposal.created_at, AssistantProposal.id)
        )
        return list(await self.session.scalars(statement))

    async def get_for_job(self, job_id: uuid.UUID) -> AssistantProposal | None:
        statement = (
            select(AssistantProposal)
            .where(AssistantProposal.job_id == job_id)
            .options(selectinload(AssistantProposal.action_records))
        )
        return await self.session.scalar(statement)

    @staticmethod
    def _uuid_or_none(value: Any) -> uuid.UUID | None:
        if value is None or isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(str(value))
