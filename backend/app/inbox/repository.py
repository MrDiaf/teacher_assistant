from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.inbox.errors import MailAttachmentNotFoundError, MailMessageNotFoundError
from app.inbox.models import (
    MailAddress,
    MailAttachment,
    MailCleanupAudit,
    MailMessage,
    MailQuarantine,
)


class InboxRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _loaded(statement):
        return statement.options(
            selectinload(MailMessage.addresses),
            selectinload(MailMessage.attachments),
        )

    async def list(
        self, *, search: str | None, archived: bool, unread_only: bool
    ) -> list[MailMessage]:
        statement = self._loaded(select(MailMessage).where(MailMessage.is_archived == archived))
        if unread_only:
            statement = statement.where(MailMessage.is_read.is_(False))
        if search:
            pattern = f"%{search.replace('%', '').replace('_', '')}%"
            statement = statement.where(
                or_(
                    MailMessage.subject.ilike(pattern),
                    MailMessage.body_text.ilike(pattern),
                    MailMessage.addresses.any(MailAddress.address.ilike(pattern)),
                    MailMessage.addresses.any(MailAddress.display_name.ilike(pattern)),
                )
            )
        statement = statement.order_by(
            MailMessage.source_date.desc().nullslast(), MailMessage.ingested_at.desc()
        ).limit(500)
        return list(await self.session.scalars(statement))

    async def get(self, message_id: uuid.UUID, *, for_update: bool = False) -> MailMessage:
        statement = self._loaded(select(MailMessage).where(MailMessage.id == message_id))
        if for_update:
            statement = statement.with_for_update()
        message = await self.session.scalar(statement)
        if message is None:
            raise MailMessageNotFoundError()
        return message

    async def get_attachment(self, attachment_id: uuid.UUID) -> MailAttachment:
        attachment = await self.session.get(MailAttachment, attachment_id)
        if attachment is None:
            raise MailAttachmentNotFoundError()
        return attachment

    async def remote_exists(self, mailbox_identity: str, uid_validity: int, uid: int) -> bool:
        return (
            await self.session.scalar(
                select(MailMessage.id).where(
                    MailMessage.mailbox_identity == mailbox_identity,
                    MailMessage.remote_uid_validity == uid_validity,
                    MailMessage.remote_uid == uid,
                )
            )
            is not None
        )

    async def quarantined_exists(self, mailbox_identity: str, uid_validity: int, uid: int) -> bool:
        return (
            await self.session.scalar(
                select(MailQuarantine.id).where(
                    MailQuarantine.mailbox_identity == mailbox_identity,
                    MailQuarantine.remote_uid_validity == uid_validity,
                    MailQuarantine.remote_uid == uid,
                )
            )
            is not None
        )

    async def secondary_duplicate(
        self, mailbox_identity: str, message_id: str | None, content_hash: str
    ) -> bool:
        if not message_id:
            return False
        return (
            await self.session.scalar(
                select(MailMessage.id).where(
                    MailMessage.mailbox_identity == mailbox_identity,
                    MailMessage.message_id == message_id,
                    MailMessage.content_hash == content_hash,
                )
            )
            is not None
        )

    async def create_message(self, values: dict[str, Any]) -> MailMessage:
        addresses = values.pop("addresses")
        attachments = values.pop("attachments")
        message = MailMessage(**values)
        message.addresses = [MailAddress(**item) for item in addresses]
        message.attachments = [MailAttachment(**item) for item in attachments]
        self.session.add(message)
        await self.session.flush()
        return message

    async def create_quarantine(self, values: dict[str, Any]) -> MailQuarantine:
        item = MailQuarantine(**values)
        self.session.add(item)
        await self.session.flush()
        return item

    async def create_cleanup_audit(self, values: dict[str, Any]) -> MailCleanupAudit:
        item = MailCleanupAudit(**values)
        self.session.add(item)
        await self.session.flush()
        return item

    async def pending_cleanup_audits(self) -> list[MailCleanupAudit]:
        return list(
            await self.session.scalars(
                select(MailCleanupAudit).where(MailCleanupAudit.status == "cleanup_failed")
            )
        )
