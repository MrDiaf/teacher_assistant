from __future__ import annotations

import asyncio
import hashlib
import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.errors import ApplicationError
from app.inbox.mail_storage import MailStorage
from app.inbox.repository import InboxRepository
from app.integrations.mail.client import ImapMailboxClient
from app.integrations.mail.parser import parse_mail
from app.integrations.mail.schemas import MailParseError
from app.integrations.models import IntegrationStatus
from app.integrations.repository import IntegrationRepository
from app.integrations.service import MailIntegrationService

logger = logging.getLogger(__name__)
_sync_lock = asyncio.Lock()


@dataclass(frozen=True)
class MailSyncResult:
    imported_count: int
    skipped_count: int
    quarantined_count: int


def mailbox_identity(host: str, port: int, mailbox: str, username: str) -> str:
    value = f"{host.lower()}\0{port}\0{mailbox}\0{username}".encode()
    return hashlib.sha256(value).hexdigest()


class MailSyncService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        settings: Settings | None = None,
        client: ImapMailboxClient | None = None,
        integration: MailIntegrationService | None = None,
        storage: MailStorage | None = None,
    ) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.integrations = IntegrationRepository(session)
        self.inbox = InboxRepository(session)
        self.integration = integration or MailIntegrationService(
            session, settings=self.settings, client=client
        )
        self.client = client or self.integration.client
        self.storage = storage or MailStorage(
            self.settings.mail_storage_root,
            self.settings.mail_max_total_storage_bytes,
        )

    async def sync(self) -> MailSyncResult:
        async with _sync_lock:
            return await self._sync_locked()

    async def _sync_locked(self) -> MailSyncResult:
        connection, credential = await self.integration.require_connected()
        connection_id = connection.id
        cursor = await self.integrations.get_cursor(connection_id, for_update=True)
        identity = mailbox_identity(
            connection.host, connection.port, connection.mailbox, connection.username
        )
        configuration = self.integration.configuration(
            host=connection.host,
            port=connection.port,
            tls_mode=connection.tls_mode,
            mailbox=connection.mailbox,
            username=connection.username,
        )
        try:
            snapshot = await self.client.fetch(
                configuration,
                credential,
                minimum_uid=(cursor.last_uid + 1 if cursor.uid_validity is not None else None),
                expected_uid_validity=cursor.uid_validity,
            )
        except ApplicationError:
            await self.integration._record_safe_failure(
                connection,
                code="mailbox_check_failed",
                message=(
                    "Mail could not be checked. Verify the dedicated mailbox connection "
                    "in Settings."
                ),
            )
            raise

        reset = cursor.uid_validity is not None and cursor.uid_validity != snapshot.uid_validity
        if reset:
            cursor.source_warning = (
                "The mail server reset its UID history. Existing local mail was preserved and "
                "messages were reconciled conservatively."
            )
            cursor.last_uid = 0
        cursor.uid_validity = snapshot.uid_validity
        imported = skipped = quarantined = 0
        for remote in sorted(snapshot.messages, key=lambda item: item.uid):
            if await self.inbox.remote_exists(identity, snapshot.uid_validity, remote.uid):
                skipped += 1
                cursor.last_uid = max(cursor.last_uid, remote.uid)
                continue
            if await self.inbox.quarantined_exists(identity, snapshot.uid_validity, remote.uid):
                skipped += 1
                cursor.last_uid = max(cursor.last_uid, remote.uid)
                continue
            message_id = uuid.uuid4()
            try:
                parsed = parse_mail(
                    remote.raw,
                    maximum_message_bytes=self.settings.mail_max_message_bytes,
                    maximum_attachment_bytes=self.settings.mail_max_attachment_bytes,
                )
                if reset and await self.inbox.secondary_duplicate(
                    identity, parsed.message_id, parsed.content_hash
                ):
                    skipped += 1
                    cursor.last_uid = max(cursor.last_uid, remote.uid)
                    continue
                attachment_values: list[dict] = []
                for attachment in parsed.attachments:
                    attachment_id = uuid.uuid4()
                    if attachment.content is None:
                        attachment_values.append(
                            {
                                "id": attachment_id,
                                "original_filename": attachment.original_filename,
                                "mime_type": attachment.mime_type,
                                "file_size": 0,
                                "content_hash": None,
                                "storage_path": None,
                                "status": "omitted",
                                "omission_reason": attachment.omission_reason,
                            }
                        )
                        continue
                    try:
                        stored = await self.storage.store(
                            message_id=message_id,
                            attachment_id=attachment_id,
                            content=attachment.content,
                        )
                        attachment_values.append(
                            {
                                "id": attachment_id,
                                "original_filename": attachment.original_filename,
                                "mime_type": attachment.mime_type,
                                "file_size": stored.file_size,
                                "content_hash": stored.content_hash,
                                "storage_path": stored.storage_path,
                                "status": "stored",
                                "omission_reason": None,
                            }
                        )
                    except ApplicationError:
                        attachment_values.append(
                            {
                                "id": attachment_id,
                                "original_filename": attachment.original_filename,
                                "mime_type": attachment.mime_type,
                                "file_size": 0,
                                "content_hash": None,
                                "storage_path": None,
                                "status": "omitted",
                                "omission_reason": "Private attachment storage was unavailable.",
                            }
                        )
                await self.inbox.create_message(
                    {
                        "id": message_id,
                        "connection_id": connection_id,
                        "mailbox_identity": identity,
                        "remote_uid_validity": snapshot.uid_validity,
                        "remote_uid": remote.uid,
                        "message_id": parsed.message_id,
                        "in_reply_to": parsed.in_reply_to,
                        "thread_references": parsed.thread_references,
                        "subject": parsed.subject,
                        "source_date": parsed.source_date,
                        "ingested_at": datetime.now(UTC),
                        "body_text": parsed.body_text,
                        "body_html": parsed.body_html,
                        "content_hash": parsed.content_hash,
                        "is_read": False,
                        "is_archived": False,
                        "forwarded_unverified": parsed.forwarded_unverified,
                        "addresses": [
                            {
                                "kind": address.kind,
                                "display_name": address.display_name,
                                "address": address.address,
                                "position": address.position,
                            }
                            for address in parsed.addresses
                        ],
                        "attachments": attachment_values,
                    }
                )
                await self.session.commit()
                imported += 1
            except MailParseError as exc:
                await self.session.rollback()
                await self.inbox.create_quarantine(
                    {
                        "connection_id": connection_id,
                        "mailbox_identity": identity,
                        "remote_uid_validity": snapshot.uid_validity,
                        "remote_uid": remote.uid,
                        "safe_error_code": exc.code,
                        "safe_error": str(exc)[:240],
                    }
                )
                await self.session.commit()
                quarantined += 1
            except Exception:
                await self.session.rollback()
                await self.storage.remove_message(message_id)
                logger.error(
                    "mail_import_failed connection=%s uid=%s error_type=internal",
                    connection_id,
                    remote.uid,
                )
                await self.inbox.create_quarantine(
                    {
                        "connection_id": connection_id,
                        "mailbox_identity": identity,
                        "remote_uid_validity": snapshot.uid_validity,
                        "remote_uid": remote.uid,
                        "safe_error_code": "import_failed",
                        "safe_error": "A message could not be stored safely.",
                    }
                )
                await self.session.commit()
                quarantined += 1
            cursor = await self.integrations.get_cursor(connection_id, for_update=True)
            cursor.last_uid = max(cursor.last_uid, remote.uid)

        now = datetime.now(UTC)
        cursor = await self.integrations.get_cursor(connection_id, for_update=True)
        cursor.last_checked_at = now
        cursor.last_success_at = now
        cursor.next_check_at = now + timedelta(seconds=self.settings.mail_sync_interval_seconds)
        cursor.failure_count = 0
        cursor.safe_error_code = None
        cursor.safe_error = None
        connection = await self.integrations.get_mail(for_update=True)
        assert connection is not None
        connection.status = IntegrationStatus.CONNECTED
        await self.session.commit()
        return MailSyncResult(imported, skipped, quarantined)
