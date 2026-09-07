from __future__ import annotations

import imaplib
import os
import stat
import uuid
from email.message import EmailMessage
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import InvalidMailConnectionError, MailConnectionError, MailStorageError
from app.inbox.mail_storage import MailStorage
from app.inbox.models import MailCleanupAudit, MailMessage, MailQuarantine
from app.inbox.service import InboxService
from app.integrations.credentials import IntegrationCredentialStore, MailCredential
from app.integrations.mail.client import ImapMailboxClient, validate_public_mail_host
from app.integrations.mail.parser import MAX_PARTS, parse_mail, sanitize_html
from app.integrations.mail.schemas import (
    MailboxConfiguration,
    MailboxSnapshot,
    MailParseError,
    RemoteMail,
)
from app.integrations.models import MailTlsMode


def message_bytes(
    *,
    subject: str = "Forwarded lecture update",
    body: str = "The lecture starts at 10:00.",
    html: str | None = None,
    attachment: bytes | None = None,
    message_id: str = "<mail-1@example.test>",
) -> bytes:
    message = EmailMessage()
    message["From"] = "School Office <office@example.edu>"
    message["To"] = "Dedicated Inbox <teacher-inbox@example.net>"
    message["Reply-To"] = "Registrar <registrar@example.edu>"
    message["Subject"] = subject
    message["Date"] = "Thu, 03 Sep 2026 09:00:00 +0200"
    message["Message-ID"] = message_id
    if html is None:
        message.set_content(body)
    else:
        message.set_content(html, subtype="html")
    if attachment is not None:
        message.add_attachment(
            attachment,
            maintype="application",
            subtype="pdf",
            filename="../../schedule.pdf",
        )
    return message.as_bytes()


def connection_payload(password: str = "mail-secret") -> dict[str, object]:
    return {
        "host": "imap.example.test",
        "port": 993,
        "tls_mode": "implicit_tls",
        "mailbox": "INBOX",
        "username": "teacher-inbox@example.test",
        "password": password,
    }


async def fake_test(self, configuration, credential):
    assert credential.password
    assert configuration.tls_mode in {MailTlsMode.IMPLICIT, MailTlsMode.STARTTLS}
    return MailboxSnapshot(uid_validity=42, messages=[])


async def connect(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> dict:
    monkeypatch.setattr(ImapMailboxClient, "test", fake_test)
    response = await client.put("/api/v1/integrations/mail", json=connection_payload())
    assert response.status_code == 200, response.text
    return response.json()


async def test_connect_reconnect_disconnect_and_missing_credentials_are_private(
    client: AsyncClient,
    session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    status = await connect(client, monkeypatch)
    assert status["connected"] is True
    assert "password" not in status
    assert "credential" not in status
    assert "mail-secret" not in str(status)

    settings = get_settings()
    secret_files = list(settings.integration_credential_root.glob("*.json"))
    assert len(secret_files) == 1
    assert stat.S_IMODE(settings.integration_credential_root.stat().st_mode) == 0o700
    assert stat.S_IMODE(secret_files[0].stat().st_mode) == 0o600
    assert "mail-secret" in secret_files[0].read_text(encoding="utf-8")

    tested = await client.post("/api/v1/integrations/mail/test")
    assert tested.status_code == 200
    replacement = connection_payload("replacement-secret")
    reconnected = await client.put("/api/v1/integrations/mail", json=replacement)
    assert reconnected.status_code == 200
    assert len(list(settings.integration_credential_root.glob("*.json"))) == 1
    assert "replacement-secret" not in reconnected.text

    secret = next(settings.integration_credential_root.glob("*.json"))
    secret.unlink()
    missing = await client.get("/api/v1/integrations/mail")
    assert missing.status_code == 200
    assert missing.json()["status"] == "reconnect_required"
    assert "replacement-secret" not in missing.text

    # Imported rows are independent from renewable credential lifecycle.
    assert await session.scalar(select(func.count()).select_from(MailMessage)) == 0
    disconnected = await client.delete("/api/v1/integrations/mail")
    assert disconnected.status_code == 204


async def test_credential_store_rejects_corrupt_and_open_permissions(tmp_path: Path) -> None:
    store = IntegrationCredentialStore(tmp_path / "credentials")
    reference = await store.write_mail("private")
    path = store.root / f"{reference}.json"
    os.chmod(path, 0o644)
    with pytest.raises(Exception, match="permissions"):
        await store.read_mail(reference)
    os.chmod(path, 0o600)
    path.write_text("not-json", encoding="utf-8")
    with pytest.raises(Exception, match="unavailable"):
        await store.read_mail(reference)


async def test_sync_deduplicates_sanitizes_and_serves_opaque_attachment(
    client: AsyncClient,
    session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await connect(client, monkeypatch)
    raw = message_bytes(
        html=(
            "<p>Hello <strong>teacher</strong></p><script>steal()</script>"
            '<img src="https://tracker.example/pixel.gif">'
            '<svg onload="steal()"></svg><form action="https://evil.example"></form>'
            '<iframe src="https://evil.example"></iframe>'
            '<a href="javascript:steal()">unsafe</a>'
            '<a href="https://school.example/update">safe</a>'
        ),
        attachment=b"bounded attachment",
    )

    async def fake_fetch(self, configuration, credential, **kwargs):
        return MailboxSnapshot(uid_validity=42, messages=[RemoteMail(uid=7, raw=raw)])

    monkeypatch.setattr(ImapMailboxClient, "fetch", fake_fetch)
    first = await client.post("/api/v1/integrations/mail/check")
    assert first.status_code == 200, first.text
    assert first.json()["imported_count"] == 1
    second = await client.post("/api/v1/integrations/mail/check")
    assert second.status_code == 200
    assert second.json()["imported_count"] == 0
    assert await session.scalar(select(func.count()).select_from(MailMessage)) == 1

    listing = await client.get("/api/v1/inbox")
    item = listing.json()[0]
    assert item["source_label"] == "Mail"
    assert item["is_read"] is False
    assert item["forwarded_unverified"] is True
    assert item["sender_address"] == "office@example.edu"

    detail_response = await client.get(f"/api/v1/inbox/{item['id']}")
    detail = detail_response.json()
    safe_html = detail["body_html"]
    for forbidden in ("script", "img", "svg", "form", "iframe", "javascript:", "onload"):
        assert forbidden not in safe_html.lower()
    assert "https://school.example/update" in safe_html
    assert "tracker.example" not in detail_response.text
    attachment = detail["attachments"][0]
    assert attachment["original_filename"] == "....schedule.pdf"
    assert "storage_path" not in detail_response.text

    download = await client.get(f"/api/v1/mail-attachments/{attachment['id']}/content")
    assert download.status_code == 200
    assert download.content == b"bounded attachment"
    assert download.headers["content-disposition"].startswith("attachment;")
    assert download.headers["x-content-type-options"] == "nosniff"


async def test_uidvalidity_reset_preserves_mail_and_reconciles_exact_secondary_match(
    client: AsyncClient,
    session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await connect(client, monkeypatch)
    raw = message_bytes()
    snapshots = iter(
        [
            MailboxSnapshot(42, [RemoteMail(1, raw)]),
            MailboxSnapshot(99, [RemoteMail(3, raw)]),
        ]
    )

    async def fake_fetch(self, configuration, credential, **kwargs):
        return next(snapshots)

    monkeypatch.setattr(ImapMailboxClient, "fetch", fake_fetch)
    assert (await client.post("/api/v1/integrations/mail/check")).json()["imported_count"] == 1
    reset = await client.post("/api/v1/integrations/mail/check")
    assert reset.status_code == 200
    assert reset.json()["imported_count"] == 0
    assert await session.scalar(select(func.count()).select_from(MailMessage)) == 1
    status = await client.get("/api/v1/integrations/mail")
    assert "reset" in status.json()["source_warning"].lower()


async def test_malformed_and_oversized_messages_are_quarantined_without_losing_prior_mail(
    client: AsyncClient,
    session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await connect(client, monkeypatch)
    valid = message_bytes()
    later_valid = message_bytes(subject="Later message", message_id="<later@example.test>")
    huge = b"From: sender@example.test\r\n\r\n" + b"x" * (get_settings().mail_max_message_bytes + 1)

    async def fake_fetch(self, configuration, credential, **kwargs):
        return MailboxSnapshot(
            42,
            [RemoteMail(1, valid), RemoteMail(2, huge), RemoteMail(3, later_valid)],
        )

    monkeypatch.setattr(ImapMailboxClient, "fetch", fake_fetch)
    result = await client.post("/api/v1/integrations/mail/check")
    assert result.status_code == 200
    assert result.json()["imported_count"] == 2
    assert result.json()["quarantined_count"] == 1
    assert await session.scalar(select(func.count()).select_from(MailMessage)) == 2
    assert await session.scalar(select(func.count()).select_from(MailQuarantine)) == 1


async def test_connection_failure_keeps_imported_mail_and_sets_safe_backoff_status(
    client: AsyncClient,
    session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await connect(client, monkeypatch)

    async def successful_fetch(self, configuration, credential, **kwargs):
        return MailboxSnapshot(42, [RemoteMail(1, message_bytes())])

    monkeypatch.setattr(ImapMailboxClient, "fetch", successful_fetch)
    assert (await client.post("/api/v1/integrations/mail/check")).status_code == 200

    async def failed_fetch(self, configuration, credential, **kwargs):
        raise MailConnectionError("Mailbox authentication failed.")

    monkeypatch.setattr(ImapMailboxClient, "fetch", failed_fetch)
    failed = await client.post("/api/v1/integrations/mail/check")
    assert failed.status_code == 502
    assert "Mailbox authentication failed" in failed.json()["message"]
    assert await session.scalar(select(func.count()).select_from(MailMessage)) == 1

    status = (await client.get("/api/v1/integrations/mail")).json()
    assert status["status"] == "error"
    assert status["safe_error_code"] == "mailbox_check_failed"
    assert status["next_check_at"] is not None
    assert "office@example.edu" not in str(status)


async def test_local_state_and_confirmed_single_delete_do_not_call_remote_mailbox(
    client: AsyncClient,
    session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await connect(client, monkeypatch)
    raws = [
        RemoteMail(1, message_bytes(subject="First", message_id="<1@test>")),
        RemoteMail(2, message_bytes(subject="Second", message_id="<2@test>")),
    ]

    async def fake_fetch(self, configuration, credential, **kwargs):
        return MailboxSnapshot(42, raws)

    monkeypatch.setattr(ImapMailboxClient, "fetch", fake_fetch)
    await client.post("/api/v1/integrations/mail/check")
    messages = (await client.get("/api/v1/inbox")).json()
    first, second = messages
    updated = await client.patch(
        f"/api/v1/inbox/{first['id']}", json={"is_read": True, "is_archived": True}
    )
    assert updated.json()["is_read"] is True
    assert updated.json()["is_archived"] is True
    assert len((await client.get("/api/v1/inbox", params={"archived": True})).json()) == 1

    deleted = await client.delete(f"/api/v1/inbox/{first['id']}")
    assert deleted.status_code == 204
    assert await session.get(MailMessage, uuid.UUID(first["id"])) is None
    assert await session.get(MailMessage, uuid.UUID(second["id"])) is not None
    assert (await client.get("/api/v1/inbox", params={"archived": True})).json() == []


async def test_failed_attachment_cleanup_is_audited_and_retryable(
    client: AsyncClient,
    session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await connect(client, monkeypatch)
    raw = message_bytes(attachment=b"private attachment")

    async def fake_fetch(self, configuration, credential, **kwargs):
        return MailboxSnapshot(42, [RemoteMail(1, raw)])

    monkeypatch.setattr(ImapMailboxClient, "fetch", fake_fetch)
    await client.post("/api/v1/integrations/mail/check")
    message_id = (await client.get("/api/v1/inbox")).json()[0]["id"]

    original_purge = MailStorage.purge_quarantine

    async def failed_purge(self, item):
        raise MailStorageError()

    monkeypatch.setattr(MailStorage, "purge_quarantine", failed_purge)
    deleted = await client.delete(f"/api/v1/inbox/{message_id}")
    assert deleted.status_code == 204
    audit = await session.scalar(select(MailCleanupAudit))
    assert audit is not None
    assert audit.status == "cleanup_failed"
    assert audit.quarantine_token is not None

    monkeypatch.setattr(MailStorage, "purge_quarantine", original_purge)
    assert await InboxService(session).retry_pending_cleanup() == 1
    await session.refresh(audit)
    assert audit.status == "cleaned"
    assert audit.quarantine_token is None


async def test_mail_host_validation_blocks_private_and_url_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def private_getaddrinfo(*args, **kwargs):
        return [(None, None, None, None, ("169.254.169.254", 993))]

    loop = __import__("asyncio").get_running_loop()
    monkeypatch.setattr(loop, "getaddrinfo", private_getaddrinfo)
    with pytest.raises(InvalidMailConnectionError):
        await validate_public_mail_host("metadata.example", 993)
    with pytest.raises(InvalidMailConnectionError):
        await validate_public_mail_host("imaps://user:secret@example.com", 993)


def test_imap_client_uses_verified_tls_readonly_select_and_peek_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple] = []

    class FakeImap:
        def __init__(self, *args, **kwargs):
            calls.append(("connect", args, kwargs))

        def login(self, username, password):
            calls.append(("login", username, "redacted"))
            return "OK", []

        def select(self, mailbox, readonly=False):
            calls.append(("select", mailbox, readonly))
            return "OK", [b"1"]

        def response(self, name):
            return name, [b"42"]

        def uid(self, command, *args):
            calls.append(("uid", command, *args))
            if command == "SEARCH":
                return "OK", [b"5"]
            return "OK", [(b"5 (BODY[])", b"From: x@example.test\r\n\r\nBody")]

        def logout(self):
            calls.append(("logout",))

    monkeypatch.setattr(imaplib, "IMAP4_SSL", FakeImap)
    configuration = MailboxConfiguration(
        "imap.example.test", 993, MailTlsMode.IMPLICIT, "INBOX", "owner", 15
    )
    snapshot = ImapMailboxClient._fetch_blocking(configuration, MailCredential("secret"), 1, True)
    assert snapshot.uid_validity == 42
    assert ("select", "INBOX", True) in calls
    assert any(
        call[:3] == ("uid", "FETCH", "5") and str(call[3]).startswith("(BODY.PEEK[]<0.")
        for call in calls
    )
    assert not any(call[0] in {"store", "copy", "expunge", "delete"} for call in calls)


def test_imap_client_restarts_uid_search_when_uidvalidity_changes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    searches: list[tuple] = []

    class FakeImap:
        def __init__(self, *args, **kwargs):
            pass

        def login(self, username, password):
            return "OK", []

        def select(self, mailbox, readonly=False):
            return "OK", [b"0"]

        def response(self, name):
            return name, [b"99"]

        def uid(self, command, *args):
            searches.append((command, *args))
            return "OK", [b""]

        def logout(self):
            pass

    monkeypatch.setattr(imaplib, "IMAP4_SSL", FakeImap)
    configuration = MailboxConfiguration(
        "imap.example.test", 993, MailTlsMode.IMPLICIT, "INBOX", "owner", 15
    )
    ImapMailboxClient._fetch_blocking(
        configuration,
        MailCredential("secret"),
        501,
        True,
        42,
    )
    assert searches == [("SEARCH", None, "UID 1:*")]


def test_imap_client_requires_verified_starttls_before_authentication(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple] = []

    class FakeImap:
        def __init__(self, *args, **kwargs):
            calls.append(("connect", args, kwargs))

        def starttls(self, *, ssl_context):
            calls.append(("starttls", ssl_context))
            return "OK", []

        def login(self, username, password):
            calls.append(("login", username, "redacted"))
            return "OK", []

        def select(self, mailbox, readonly=False):
            calls.append(("select", mailbox, readonly))
            return "OK", [b"0"]

        def response(self, name):
            return name, [b"42"]

        def logout(self):
            calls.append(("logout",))

    monkeypatch.setattr(imaplib, "IMAP4", FakeImap)
    configuration = MailboxConfiguration(
        "imap.example.test", 143, MailTlsMode.STARTTLS, "INBOX", "owner", 15
    )
    snapshot = ImapMailboxClient._fetch_blocking(
        configuration, MailCredential("secret"), None, False
    )
    assert snapshot.uid_validity == 42
    assert [call[0] for call in calls].index("starttls") < [call[0] for call in calls].index(
        "login"
    )
    assert ("select", "INBOX", True) in calls


def test_mime_limits_and_passive_html_sanitizer() -> None:
    nested = EmailMessage()
    nested["From"] = "x@example.test"
    nested["To"] = "y@example.test"
    nested.make_mixed()
    for index in range(MAX_PARTS + 1):
        child = EmailMessage()
        child.set_content(f"part {index}")
        nested.attach(child)
    with pytest.raises(MailParseError, match="MIME limits"):
        parse_mail(
            nested.as_bytes(),
            maximum_message_bytes=10_000_000,
            maximum_attachment_bytes=1_000_000,
        )
    safe = sanitize_html(
        '<p onclick="x()">ok</p><img src="https://tracker"><script>x()</script>'
        '<a href="data:text/html,bad">bad</a>'
    )
    assert safe == "<p>ok</p>bad"

    omitted = parse_mail(
        message_bytes(attachment=b"oversized"),
        maximum_message_bytes=100_000,
        maximum_attachment_bytes=4,
    ).attachments[0]
    assert omitted.content is None
    assert "size limit" in (omitted.omission_reason or "")
