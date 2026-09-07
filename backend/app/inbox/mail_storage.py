from __future__ import annotations

import hashlib
import os
import shutil
import stat
import uuid
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from starlette.concurrency import run_in_threadpool

from app.core.errors import MailAttachmentUnavailableError, MailStorageError
from app.inbox.models import MailAttachment


@dataclass(frozen=True)
class StoredMailAttachment:
    attachment_id: uuid.UUID
    storage_path: str
    content_hash: str
    file_size: int


@dataclass(frozen=True)
class QuarantinedMail:
    message_id: uuid.UUID
    original: Path
    quarantined: Path


class MailStorage:
    def __init__(self, root: Path, maximum_total_bytes: int) -> None:
        self.root = root.resolve()
        self.maximum_total_bytes = maximum_total_bytes

    async def store(
        self, *, message_id: uuid.UUID, attachment_id: uuid.UUID, content: bytes
    ) -> StoredMailAttachment:
        return await run_in_threadpool(self._store, message_id, attachment_id, content)

    async def ensure_root(self) -> None:
        await run_in_threadpool(self._ensure_root)

    def _store(
        self, message_id: uuid.UUID, attachment_id: uuid.UUID, content: bytes
    ) -> StoredMailAttachment:
        self._ensure_root()
        try:
            used = sum(
                path.stat().st_size
                for path in self.root.rglob("*.bin")
                if path.is_file() and not path.is_symlink()
            )
        except OSError as exc:
            raise MailStorageError() from exc
        if used + len(content) > self.maximum_total_bytes:
            raise MailStorageError("Private mail attachment storage is full.")
        relative = PurePosixPath(str(message_id), f"{attachment_id}.bin")
        destination = self._absolute(relative)
        destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        temporary = self._absolute(PurePosixPath(".uploads", f"{attachment_id}.tmp"))
        temporary.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, destination)
        except Exception as exc:
            temporary.unlink(missing_ok=True)
            destination.unlink(missing_ok=True)
            raise MailStorageError() from exc
        return StoredMailAttachment(
            attachment_id=attachment_id,
            storage_path=relative.as_posix(),
            content_hash=hashlib.sha256(content).hexdigest(),
            file_size=len(content),
        )

    async def resolve(self, attachment: MailAttachment) -> Path:
        return await run_in_threadpool(self._resolve, attachment)

    def _resolve(self, attachment: MailAttachment) -> Path:
        if attachment.status != "stored" or not attachment.storage_path:
            raise MailAttachmentUnavailableError()
        expected = PurePosixPath(str(attachment.message_id), f"{attachment.id}.bin")
        if PurePosixPath(attachment.storage_path) != expected:
            raise MailAttachmentUnavailableError()
        path = self._absolute(expected)
        try:
            file_stat = path.lstat()
            if (
                not stat.S_ISREG(file_stat.st_mode)
                or stat.S_ISLNK(file_stat.st_mode)
                or file_stat.st_size != attachment.file_size
                or self._hash(path) != attachment.content_hash
            ):
                raise MailAttachmentUnavailableError()
        except OSError as exc:
            raise MailAttachmentUnavailableError() from exc
        return path

    async def remove_message(self, message_id: uuid.UUID) -> None:
        await run_in_threadpool(shutil.rmtree, self._absolute(PurePosixPath(str(message_id))), True)

    async def quarantine_message(self, message_id: uuid.UUID) -> QuarantinedMail | None:
        return await run_in_threadpool(self._quarantine, message_id)

    def _quarantine(self, message_id: uuid.UUID) -> QuarantinedMail | None:
        original = self._absolute(PurePosixPath(str(message_id)))
        if not original.exists():
            return None
        quarantined = self._absolute(PurePosixPath(".trash", uuid.uuid4().hex))
        quarantined.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        try:
            os.replace(original, quarantined)
        except OSError as exc:
            raise MailStorageError("Mail attachments could not be prepared for deletion.") from exc
        return QuarantinedMail(message_id, original, quarantined)

    async def restore_quarantine(self, item: QuarantinedMail | None) -> None:
        if item is None:
            return
        await run_in_threadpool(self._restore_quarantine, item)

    def _restore_quarantine(self, item: QuarantinedMail) -> None:
        if item.quarantined.exists():
            item.original.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            os.replace(item.quarantined, item.original)

    async def purge_quarantine(self, item: QuarantinedMail | None) -> None:
        if item is not None:
            await run_in_threadpool(shutil.rmtree, item.quarantined)

    async def purge_quarantine_token(self, token: str) -> None:
        relative = PurePosixPath(token)
        if len(relative.parts) != 2 or relative.parts[0] != ".trash":
            raise MailStorageError("A cleanup record failed its storage check.")
        try:
            uuid.UUID(hex=relative.parts[1])
        except ValueError as exc:
            raise MailStorageError("A cleanup record failed its storage check.") from exc
        await run_in_threadpool(shutil.rmtree, self._absolute(relative), True)

    def _absolute(self, relative: PurePosixPath) -> Path:
        if relative.is_absolute() or ".." in relative.parts:
            raise MailStorageError()
        path = self.root.joinpath(*relative.parts)
        if not path.is_relative_to(self.root):
            raise MailStorageError()
        return path

    @staticmethod
    def _hash(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                digest.update(chunk)
        return digest.hexdigest()

    def _ensure_root(self) -> None:
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(self.root, 0o700)
