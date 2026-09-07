from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.inbox.mail_storage import MailStorage
from app.inbox.models import MailAddressKind, MailMessage
from app.inbox.repository import InboxRepository
from app.inbox.schemas import (
    MailAddressResponse,
    MailAttachmentResponse,
    MailMessageListResponse,
    MailMessageResponse,
    MailStateUpdate,
)


@dataclass(frozen=True)
class AttachmentDownload:
    path: object
    filename: str
    mime_type: str


class InboxService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        settings: Settings | None = None,
        storage: MailStorage | None = None,
    ) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.repository = InboxRepository(session)
        self.storage = storage or MailStorage(
            self.settings.mail_storage_root,
            self.settings.mail_max_total_storage_bytes,
        )

    async def list_messages(
        self, *, search: str | None, archived: bool, unread_only: bool
    ) -> list[MailMessageListResponse]:
        messages = await self.repository.list(
            search=search, archived=archived, unread_only=unread_only
        )
        return [self._list_response(message) for message in messages]

    async def get_message(self, message_id: uuid.UUID) -> MailMessageResponse:
        message = await self.repository.get(message_id)
        return self._detail_response(message)

    async def update_state(
        self, message_id: uuid.UUID, payload: MailStateUpdate
    ) -> MailMessageResponse:
        message = await self.repository.get(message_id, for_update=True)
        if payload.is_read is not None:
            message.is_read = payload.is_read
        if payload.is_archived is not None:
            message.is_archived = payload.is_archived
        await self.session.commit()
        return self._detail_response(await self.repository.get(message_id))

    async def attachment(self, attachment_id: uuid.UUID) -> AttachmentDownload:
        attachment = await self.repository.get_attachment(attachment_id)
        path = await self.storage.resolve(attachment)
        return AttachmentDownload(path, attachment.original_filename, attachment.mime_type)

    async def delete_message(self, message_id: uuid.UUID) -> None:
        message = await self.repository.get(message_id, for_update=True)
        quarantine = await self.storage.quarantine_message(message_id)
        try:
            await self.session.delete(message)
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            await self.storage.restore_quarantine(quarantine)
            raise
        if quarantine is None:
            return
        try:
            await self.storage.purge_quarantine(quarantine)
        except Exception:
            await self.repository.create_cleanup_audit(
                {
                    "deleted_message_id": message_id,
                    "status": "cleanup_failed",
                    "quarantine_token": quarantine.quarantined.relative_to(
                        self.storage.root
                    ).as_posix(),
                    "safe_error": "A quarantined attachment directory still needs cleanup.",
                }
            )
            await self.session.commit()

    async def retry_pending_cleanup(self) -> int:
        recovered = 0
        for audit in await self.repository.pending_cleanup_audits():
            if not audit.quarantine_token:
                continue
            try:
                await self.storage.purge_quarantine_token(audit.quarantine_token)
            except Exception:
                continue
            audit.status = "cleaned"
            audit.safe_error = None
            audit.quarantine_token = None
            recovered += 1
        if recovered:
            await self.session.commit()
        return recovered

    @staticmethod
    def _sender(message: MailMessage):
        return next(
            (address for address in message.addresses if address.kind == MailAddressKind.FROM),
            None,
        )

    def _list_response(self, message: MailMessage) -> MailMessageListResponse:
        sender = self._sender(message)
        recipients = [
            address.address
            for address in sorted(message.addresses, key=lambda item: item.position)
            if address.kind == MailAddressKind.TO
        ]
        return MailMessageListResponse(
            id=message.id,
            subject=message.subject,
            sender_name=sender.display_name if sender else None,
            sender_address=sender.address if sender else "Unknown sender",
            recipients=recipients,
            source_date=message.source_date,
            ingested_at=message.ingested_at,
            attachment_count=sum(item.status == "stored" for item in message.attachments),
            omitted_attachment_count=sum(item.status == "omitted" for item in message.attachments),
            is_read=message.is_read,
            is_archived=message.is_archived,
            forwarded_unverified=message.forwarded_unverified,
        )

    def _detail_response(self, message: MailMessage) -> MailMessageResponse:
        summary = self._list_response(message)
        return MailMessageResponse(
            **summary.model_dump(),
            message_id=message.message_id,
            in_reply_to=message.in_reply_to,
            thread_references=message.thread_references,
            body_text=message.body_text,
            body_html=message.body_html,
            addresses=[
                MailAddressResponse.model_validate(item)
                for item in sorted(
                    message.addresses,
                    key=lambda address: (address.kind.value, address.position),
                )
            ],
            attachments=[
                MailAttachmentResponse.model_validate(item) for item in message.attachments
            ],
        )
