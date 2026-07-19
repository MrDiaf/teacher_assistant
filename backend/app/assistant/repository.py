from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.assistant.models import (
    AssistantConversation,
    AssistantJob,
    AssistantJobStatus,
    AssistantMessage,
    AssistantMessageRole,
)
from app.core.errors import (
    AssistantConversationNotFoundError,
    AssistantJobNotFoundError,
)


class AssistantRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_conversations(self) -> list[AssistantConversation]:
        statement = select(AssistantConversation).order_by(
            AssistantConversation.updated_at.desc(), AssistantConversation.created_at.desc()
        )
        return list(await self.session.scalars(statement))

    async def create_conversation(self, title: str) -> AssistantConversation:
        conversation = AssistantConversation(title=title)
        self.session.add(conversation)
        await self.session.flush()
        return conversation

    async def get_conversation(
        self, conversation_id: uuid.UUID, *, for_update: bool = False
    ) -> AssistantConversation:
        statement = select(AssistantConversation).where(AssistantConversation.id == conversation_id)
        if for_update:
            statement = statement.with_for_update()
        conversation = await self.session.scalar(statement)
        if conversation is None:
            raise AssistantConversationNotFoundError()
        return conversation

    async def list_messages(self, conversation_id: uuid.UUID) -> list[AssistantMessage]:
        await self.get_conversation(conversation_id)
        statement = (
            select(AssistantMessage)
            .where(AssistantMessage.conversation_id == conversation_id)
            .order_by(AssistantMessage.created_at, AssistantMessage.id)
        )
        return list(await self.session.scalars(statement))

    async def create_message(
        self,
        conversation_id: uuid.UUID,
        *,
        role: AssistantMessageRole,
        content: str,
        job_id: uuid.UUID | None = None,
    ) -> AssistantMessage:
        message = AssistantMessage(
            conversation_id=conversation_id,
            role=role,
            content=content,
            job_id=job_id,
        )
        self.session.add(message)
        await self.session.flush()
        return message

    async def get_message(self, message_id: uuid.UUID) -> AssistantMessage:
        message = await self.session.get(AssistantMessage, message_id)
        if message is None:
            raise AssistantJobNotFoundError()
        return message

    async def create_job(
        self,
        conversation_id: uuid.UUID,
        owner_message_id: uuid.UUID,
    ) -> AssistantJob:
        job = AssistantJob(
            conversation_id=conversation_id,
            owner_message_id=owner_message_id,
            status=AssistantJobStatus.QUEUED,
        )
        self.session.add(job)
        await self.session.flush()
        return job

    async def get_job(self, job_id: uuid.UUID, *, for_update: bool = False) -> AssistantJob:
        statement = select(AssistantJob).where(AssistantJob.id == job_id)
        if for_update:
            statement = statement.with_for_update()
        job = await self.session.scalar(statement)
        if job is None:
            raise AssistantJobNotFoundError()
        return job

    async def list_jobs(self, conversation_id: uuid.UUID) -> list[AssistantJob]:
        await self.get_conversation(conversation_id)
        statement = (
            select(AssistantJob)
            .where(AssistantJob.conversation_id == conversation_id)
            .order_by(AssistantJob.created_at, AssistantJob.id)
        )
        return list(await self.session.scalars(statement))

    async def update_job(self, job_id: uuid.UUID, changes: dict[str, Any]) -> AssistantJob:
        job = await self.get_job(job_id, for_update=True)
        for field, value in changes.items():
            setattr(job, field, value)
        await self.session.flush()
        return job

    async def get_assistant_message_for_job(self, job_id: uuid.UUID) -> AssistantMessage | None:
        return await self.session.scalar(
            select(AssistantMessage).where(
                AssistantMessage.job_id == job_id,
                AssistantMessage.role == AssistantMessageRole.ASSISTANT,
            )
        )
