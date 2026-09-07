from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.errors import MailConnectionError, MailReconnectRequiredError
from app.integrations.credentials import (
    CredentialUnavailableError,
    IntegrationCredentialStore,
    MailCredential,
)
from app.integrations.mail.client import ImapMailboxClient
from app.integrations.mail.schemas import MailboxConfiguration
from app.integrations.models import IntegrationConnection, IntegrationStatus
from app.integrations.repository import IntegrationRepository
from app.integrations.schemas import MailConnectionInput, MailConnectionResponse


class MailIntegrationService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        settings: Settings | None = None,
        credentials: IntegrationCredentialStore | None = None,
        client: ImapMailboxClient | None = None,
    ) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.repository = IntegrationRepository(session)
        self.credentials = credentials or IntegrationCredentialStore(
            self.settings.integration_credential_root
        )
        self.client = client or ImapMailboxClient()

    def configuration(
        self,
        *,
        host: str,
        port: int,
        tls_mode,
        mailbox: str,
        username: str,
    ) -> MailboxConfiguration:
        return MailboxConfiguration(
            host=host,
            port=port,
            tls_mode=tls_mode,
            mailbox=mailbox,
            username=username,
            timeout_seconds=self.settings.mail_timeout_seconds,
            maximum_message_bytes=self.settings.mail_max_message_bytes,
        )

    async def status(self) -> MailConnectionResponse:
        connection = await self.repository.get_mail()
        if connection is None:
            return MailConnectionResponse(connected=False)
        cursor = await self.repository.get_cursor(connection.id)
        try:
            await self.credentials.read_mail(connection.credential_ref)
        except CredentialUnavailableError:
            if connection.status != IntegrationStatus.RECONNECT_REQUIRED:
                connection.status = IntegrationStatus.RECONNECT_REQUIRED
                cursor.safe_error_code = "credential_unavailable"
                cursor.safe_error = "Reconnect the dedicated mailbox to resume checks."
                await self.session.commit()
        return MailConnectionResponse(
            connected=(
                connection.credential_ref is not None
                and connection.status == IntegrationStatus.CONNECTED
            ),
            status=connection.status,
            host=connection.host,
            port=connection.port,
            tls_mode=connection.tls_mode,
            mailbox=connection.mailbox,
            username=connection.username,
            last_checked_at=cursor.last_checked_at,
            last_success_at=cursor.last_success_at,
            next_check_at=cursor.next_check_at,
            safe_error_code=cursor.safe_error_code,
            safe_error=cursor.safe_error,
            source_warning=cursor.source_warning,
            quarantined_count=await self.repository.quarantine_count(connection.id),
        )

    async def connect(self, payload: MailConnectionInput) -> MailConnectionResponse:
        configuration = self.configuration(
            host=payload.host,
            port=payload.port,
            tls_mode=payload.tls_mode,
            mailbox=payload.mailbox,
            username=payload.username,
        )
        credential = MailCredential(password=payload.password.get_secret_value())
        snapshot = await self.client.test(configuration, credential)
        current = await self.repository.get_mail()
        old_reference = current.credential_ref if current else None
        changed_mailbox = bool(
            current
            and (
                current.host != payload.host.lower().rstrip(".")
                or current.port != payload.port
                or current.tls_mode != payload.tls_mode
                or current.mailbox != payload.mailbox
                or current.username != payload.username
            )
        )
        new_reference = await self.credentials.write_mail(credential.password)
        try:
            connection = await self.repository.upsert_mail(
                {
                    "host": payload.host.lower().rstrip("."),
                    "port": payload.port,
                    "tls_mode": payload.tls_mode,
                    "mailbox": payload.mailbox,
                    "username": payload.username,
                    "credential_ref": new_reference,
                    "status": IntegrationStatus.CONNECTED,
                }
            )
            cursor = await self.repository.get_cursor(connection.id, for_update=True)
            if changed_mailbox:
                cursor.uid_validity = None
                cursor.last_uid = 0
                cursor.source_warning = None
            elif cursor.uid_validity is None:
                cursor.uid_validity = snapshot.uid_validity
            cursor.failure_count = 0
            cursor.safe_error = None
            cursor.safe_error_code = None
            cursor.next_check_at = datetime.now(UTC)
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            await self.credentials.delete(new_reference)
            raise
        if old_reference and old_reference != new_reference:
            try:
                await self.credentials.delete(old_reference)
            except CredentialUnavailableError:
                pass
        return await self.status()

    async def test_existing(self) -> MailConnectionResponse:
        connection, credential = await self.require_connected()
        configuration = self.configuration(
            host=connection.host,
            port=connection.port,
            tls_mode=connection.tls_mode,
            mailbox=connection.mailbox,
            username=connection.username,
        )
        try:
            await self.client.test(configuration, credential)
        except MailConnectionError:
            await self._record_safe_failure(
                connection,
                code="connection_test_failed",
                message="The mailbox test failed. Check the app password and TLS settings.",
            )
            raise
        connection.status = IntegrationStatus.CONNECTED
        cursor = await self.repository.get_cursor(connection.id, for_update=True)
        cursor.safe_error = None
        cursor.safe_error_code = None
        await self.session.commit()
        return await self.status()

    async def disconnect(self) -> MailConnectionResponse:
        connection = await self.repository.get_mail(for_update=True)
        if connection is None:
            return MailConnectionResponse(connected=False)
        await self.credentials.delete(connection.credential_ref)
        connection.credential_ref = None
        connection.status = IntegrationStatus.RECONNECT_REQUIRED
        cursor = await self.repository.get_cursor(connection.id, for_update=True)
        cursor.next_check_at = None
        cursor.safe_error_code = "disconnected"
        cursor.safe_error = "Mailbox disconnected. Imported Inbox mail remains available."
        await self.session.commit()
        return await self.status()

    async def require_connected(self) -> tuple[IntegrationConnection, MailCredential]:
        connection = await self.repository.get_mail()
        if connection is None or connection.credential_ref is None:
            raise MailReconnectRequiredError()
        try:
            credential = await self.credentials.read_mail(connection.credential_ref)
        except CredentialUnavailableError as exc:
            connection.status = IntegrationStatus.RECONNECT_REQUIRED
            cursor = await self.repository.get_cursor(connection.id, for_update=True)
            cursor.next_check_at = None
            cursor.safe_error_code = "credential_unavailable"
            cursor.safe_error = "Reconnect the dedicated mailbox to resume checks."
            await self.session.commit()
            raise MailReconnectRequiredError() from exc
        return connection, credential

    async def _record_safe_failure(
        self, connection: IntegrationConnection, *, code: str, message: str
    ) -> None:
        connection.status = IntegrationStatus.ERROR
        cursor = await self.repository.get_cursor(connection.id, for_update=True)
        cursor.last_checked_at = datetime.now(UTC)
        cursor.failure_count += 1
        cursor.safe_error_code = code
        cursor.safe_error = message
        backoff = min(
            self.settings.mail_sync_interval_seconds * (2 ** min(cursor.failure_count, 6)),
            3600,
        )
        cursor.next_check_at = datetime.now(UTC) + timedelta(seconds=backoff)
        await self.session.commit()
