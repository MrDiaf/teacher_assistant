from __future__ import annotations

import asyncio
import imaplib
import ipaddress
import re
import socket
import ssl
from collections.abc import Callable

from app.core.errors import InvalidMailConnectionError, MailConnectionError
from app.integrations.credentials import MailCredential
from app.integrations.mail.schemas import MailboxConfiguration, MailboxSnapshot, RemoteMail
from app.integrations.models import MailTlsMode

HOST_PATTERN = re.compile(r"^(?=.{1,253}$)(?!-)(?:[A-Za-z0-9-]{1,63}\.)*[A-Za-z0-9-]{1,63}$")


async def validate_public_mail_host(host: str, port: int) -> str:
    normalized = host.strip().rstrip(".").lower()
    if (
        not HOST_PATTERN.fullmatch(normalized)
        or "://" in normalized
        or "@" in normalized
        or "/" in normalized
    ):
        raise InvalidMailConnectionError("Enter a valid public IMAP hostname without a URL.")
    try:
        addresses = await asyncio.get_running_loop().getaddrinfo(
            normalized, port, type=socket.SOCK_STREAM
        )
    except OSError as exc:
        raise MailConnectionError("The IMAP host could not be resolved.") from exc
    resolved = {entry[4][0] for entry in addresses}
    if not resolved or any(not ipaddress.ip_address(address).is_global for address in resolved):
        raise InvalidMailConnectionError(
            "The IMAP host must resolve only to public network addresses."
        )
    return normalized


class ImapMailboxClient:
    """One-shot verified-TLS IMAP client that only issues read operations."""

    def __init__(
        self,
        resolver: Callable[[str, int], object] | None = None,
    ) -> None:
        self.resolver = resolver

    async def test(
        self, configuration: MailboxConfiguration, credential: MailCredential
    ) -> MailboxSnapshot:
        return await self.fetch(configuration, credential, minimum_uid=None, fetch_messages=False)

    async def fetch(
        self,
        configuration: MailboxConfiguration,
        credential: MailCredential,
        *,
        minimum_uid: int | None,
        expected_uid_validity: int | None = None,
        fetch_messages: bool = True,
    ) -> MailboxSnapshot:
        if self.resolver is None:
            host = await validate_public_mail_host(configuration.host, configuration.port)
        else:
            result = self.resolver(configuration.host, configuration.port)
            host = await result if hasattr(result, "__await__") else result
        safe_configuration = MailboxConfiguration(
            host=str(host),
            port=configuration.port,
            tls_mode=configuration.tls_mode,
            mailbox=configuration.mailbox,
            username=configuration.username,
            timeout_seconds=configuration.timeout_seconds,
            maximum_message_bytes=configuration.maximum_message_bytes,
            maximum_messages_per_sync=configuration.maximum_messages_per_sync,
        )
        try:
            return await asyncio.to_thread(
                self._fetch_blocking,
                safe_configuration,
                credential,
                minimum_uid,
                fetch_messages,
                expected_uid_validity,
            )
        except (InvalidMailConnectionError, MailConnectionError):
            raise
        except (imaplib.IMAP4.error, OSError, ssl.SSLError, TimeoutError) as exc:
            raise MailConnectionError(
                "The mailbox rejected the connection or could not be reached. "
                "Check its TLS, app password, and mailbox settings."
            ) from exc

    @staticmethod
    def _fetch_blocking(
        configuration: MailboxConfiguration,
        credential: MailCredential,
        minimum_uid: int | None,
        fetch_messages: bool,
        expected_uid_validity: int | None = None,
    ) -> MailboxSnapshot:
        context = ssl.create_default_context()
        client: imaplib.IMAP4
        if configuration.tls_mode == MailTlsMode.IMPLICIT:
            client = imaplib.IMAP4_SSL(
                configuration.host,
                configuration.port,
                ssl_context=context,
                timeout=configuration.timeout_seconds,
            )
        else:
            client = imaplib.IMAP4(
                configuration.host,
                configuration.port,
                timeout=configuration.timeout_seconds,
            )
            status, _ = client.starttls(ssl_context=context)
            if status != "OK":
                raise MailConnectionError("The IMAP server did not accept verified STARTTLS.")
        try:
            status, _ = client.login(configuration.username, credential.password)
            if status != "OK":
                raise MailConnectionError("The IMAP server rejected the mailbox credentials.")
            status, _ = client.select(configuration.mailbox, readonly=True)
            if status != "OK":
                raise MailConnectionError("The configured mailbox could not be opened read-only.")
            uid_response = client.response("UIDVALIDITY")[1]
            if not uid_response:
                raise MailConnectionError("The IMAP server did not provide UIDVALIDITY.")
            uid_validity = int(uid_response[0])
            if not fetch_messages:
                return MailboxSnapshot(uid_validity=uid_validity, messages=[])
            search_start = (
                minimum_uid
                if expected_uid_validity == uid_validity and minimum_uid is not None
                else 1
            )
            criterion = f"UID {max(1, search_start)}:*"
            status, data = client.uid("SEARCH", None, criterion)
            if status != "OK":
                raise MailConnectionError("The IMAP server could not list mailbox messages.")
            uid_data = data[0] or b""
            if len(uid_data) > 1024 * 1024:
                raise MailConnectionError("The IMAP message listing exceeded a safe limit.")
            uids = [int(value) for value in uid_data.split() if value.isdigit()]
            uids = uids[: configuration.maximum_messages_per_sync]
            messages: list[RemoteMail] = []
            for uid in uids:
                if minimum_uid is not None and uid < minimum_uid:
                    continue
                fetch_limit = configuration.maximum_message_bytes + 1
                status, fetched = client.uid("FETCH", str(uid), f"(BODY.PEEK[]<0.{fetch_limit}>)")
                if status != "OK":
                    raise MailConnectionError("The IMAP server could not read a mailbox message.")
                raw = next(
                    (entry[1] for entry in fetched if isinstance(entry, tuple) and len(entry) > 1),
                    None,
                )
                if not isinstance(raw, bytes):
                    raise MailConnectionError(
                        "The IMAP server returned an invalid message payload."
                    )
                if len(raw) > configuration.maximum_message_bytes:
                    raw = b""
                messages.append(RemoteMail(uid=uid, raw=raw))
            return MailboxSnapshot(uid_validity=uid_validity, messages=messages)
        finally:
            try:
                client.logout()
            except Exception:
                pass
