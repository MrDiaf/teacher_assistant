from __future__ import annotations

import json
import os
import stat
import uuid
from dataclasses import dataclass
from pathlib import Path

from starlette.concurrency import run_in_threadpool


class CredentialUnavailableError(Exception):
    """A renewable credential is missing or fails private-storage validation."""


@dataclass(frozen=True)
class MailCredential:
    password: str


class IntegrationCredentialStore:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    async def write_mail(self, password: str) -> str:
        reference = str(uuid.uuid4())
        await run_in_threadpool(self._write, reference, password)
        return reference

    async def ensure_root(self) -> None:
        await run_in_threadpool(self._ensure_root)

    async def replace_mail(self, reference: str | None, password: str) -> str:
        new_reference = await self.write_mail(password)
        if reference:
            await self.delete(reference)
        return new_reference

    async def read_mail(self, reference: str | None) -> MailCredential:
        if reference is None:
            raise CredentialUnavailableError("Credential reference is missing.")
        return await run_in_threadpool(self._read, reference)

    async def delete(self, reference: str | None) -> None:
        if reference is None:
            return
        await run_in_threadpool(self._delete, reference)

    def _path(self, reference: str) -> Path:
        try:
            normalized = str(uuid.UUID(reference))
        except (ValueError, AttributeError) as exc:
            raise CredentialUnavailableError("Credential reference is invalid.") from exc
        return self.root / f"{normalized}.json"

    def _write(self, reference: str, password: str) -> None:
        self._ensure_root()
        target = self._path(reference)
        temporary = self.root / f".{reference}.{uuid.uuid4().hex}.tmp"
        payload = json.dumps({"version": 1, "password": password}, ensure_ascii=False).encode()
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temporary, 0o600)
            os.replace(temporary, target)
        finally:
            if temporary.exists():
                temporary.unlink()

    def _read(self, reference: str) -> MailCredential:
        target = self._path(reference)
        try:
            root_mode = stat.S_IMODE(self.root.stat().st_mode)
            file_stat = target.lstat()
            if root_mode != 0o700 or stat.S_ISLNK(file_stat.st_mode):
                raise CredentialUnavailableError("Credential storage permissions are invalid.")
            if stat.S_IMODE(file_stat.st_mode) != 0o600 or not stat.S_ISREG(file_stat.st_mode):
                raise CredentialUnavailableError("Credential file permissions are invalid.")
            if file_stat.st_size > 16_384:
                raise CredentialUnavailableError("Credential file is invalid.")
            payload = json.loads(target.read_text(encoding="utf-8"))
        except CredentialUnavailableError:
            raise
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise CredentialUnavailableError("Credential file is unavailable.") from exc
        if (
            not isinstance(payload, dict)
            or payload.get("version") != 1
            or not isinstance(payload.get("password"), str)
            or not payload["password"]
        ):
            raise CredentialUnavailableError("Credential file is invalid.")
        return MailCredential(password=payload["password"])

    def _delete(self, reference: str) -> None:
        target = self._path(reference)
        try:
            target.unlink(missing_ok=True)
        except OSError as exc:
            raise CredentialUnavailableError("Credential could not be removed.") from exc

    def _ensure_root(self) -> None:
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(self.root, 0o700)
