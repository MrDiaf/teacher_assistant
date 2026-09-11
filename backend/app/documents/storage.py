from __future__ import annotations

import io
import os
import shutil
import stat
import uuid
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from fastapi.concurrency import run_in_threadpool

from app.documents.errors import DocumentStorageError, DocumentStorageMismatchError

INITIAL_MAIN_TEX = r"""\documentclass{article}
\begin{document}
Hello, Teacher Assistant!
\end{document}
"""


@dataclass(frozen=True)
class QuarantinedDocument:
    original: Path
    quarantined: Path


class DocumentStorage:
    def __init__(self, root: Path, max_source_bytes: int, max_files: int = 1000) -> None:
        self.root = root.absolute()
        self.max_source_bytes = max_source_bytes
        self.max_files = max_files

    async def ensure_root(self) -> None:
        await run_in_threadpool(self._ensure_root)

    async def create_project(self, project_id: uuid.UUID) -> None:
        await run_in_threadpool(self._create_project, project_id)

    async def remove_created_project(self, project_id: uuid.UUID) -> None:
        await run_in_threadpool(self._remove_created_project, project_id)

    async def validate_project(self, project_id: uuid.UUID) -> None:
        await run_in_threadpool(self._validated_source_files, project_id)

    async def read_main_tex(self, project_id: uuid.UUID) -> bytes:
        return await run_in_threadpool(self._read_main_tex, project_id)

    async def build_source_zip(self, project_id: uuid.UUID) -> bytes:
        return await run_in_threadpool(self._build_source_zip, project_id)

    async def quarantine_project(self, project_id: uuid.UUID) -> QuarantinedDocument:
        return await run_in_threadpool(self._quarantine_project, project_id)

    async def restore(self, item: QuarantinedDocument) -> None:
        await run_in_threadpool(self._restore, item)

    async def purge(self, item: QuarantinedDocument) -> None:
        await run_in_threadpool(self._purge, item)

    def _ensure_root(self) -> None:
        if self.root.exists() or self.root.is_symlink():
            info = self.root.lstat()
            if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
                raise DocumentStorageError("The configured document storage root is unsafe.")
        else:
            self.root.mkdir(mode=0o700, parents=True)
        os.chmod(self.root, 0o700)
        trash = self.root / ".trash"
        if trash.exists() or trash.is_symlink():
            info = trash.lstat()
            if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
                raise DocumentStorageError("The document deletion quarantine is unsafe.")
        else:
            trash.mkdir(mode=0o700)
        os.chmod(trash, 0o700)

    def _project(self, project_id: uuid.UUID) -> Path:
        if not isinstance(project_id, uuid.UUID):
            raise DocumentStorageError("The document storage identity is invalid.")
        return self.root / str(project_id)

    @staticmethod
    def _require_directory(path: Path) -> None:
        try:
            info = path.lstat()
        except FileNotFoundError as exc:
            raise DocumentStorageMismatchError() from exc
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
            raise DocumentStorageMismatchError()

    @staticmethod
    def _require_regular(path: Path) -> os.stat_result:
        try:
            info = path.lstat()
        except FileNotFoundError as exc:
            raise DocumentStorageMismatchError() from exc
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise DocumentStorageMismatchError()
        return info

    def _create_project(self, project_id: uuid.UUID) -> None:
        self._ensure_root()
        destination = self._project(project_id)
        if destination.exists() or destination.is_symlink():
            raise DocumentStorageError("Document source storage already exists for this project.")
        staging = self.root / f".create-{project_id}-{uuid.uuid4().hex}"
        try:
            staging.mkdir(mode=0o700)
            source = staging / "source"
            build = staging / "build"
            source.mkdir(mode=0o700)
            build.mkdir(mode=0o700)
            temporary = source / f".main.tex-{uuid.uuid4().hex}.tmp"
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            descriptor = os.open(temporary, flags, 0o600)
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(INITIAL_MAIN_TEX.encode("utf-8"))
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, source / "main.tex")
            os.replace(staging, destination)
        except Exception as exc:
            if staging.exists() and not staging.is_symlink():
                shutil.rmtree(staging)
            if isinstance(exc, DocumentStorageError):
                raise
            raise DocumentStorageError("The private document source could not be created.") from exc

    def _remove_created_project(self, project_id: uuid.UUID) -> None:
        project = self._project(project_id)
        if project.exists() and not project.is_symlink():
            shutil.rmtree(project)

    def _validated_source_files(self, project_id: uuid.UUID) -> list[tuple[PurePosixPath, Path]]:
        self._ensure_root()
        project = self._project(project_id)
        self._require_directory(project)
        source = project / "source"
        build = project / "build"
        self._require_directory(source)
        self._require_directory(build)
        result: list[tuple[PurePosixPath, Path]] = []
        seen: set[str] = set()
        total = 0

        def visit(directory: Path, relative: PurePosixPath) -> None:
            nonlocal total
            try:
                entries = sorted(os.scandir(directory), key=lambda entry: entry.name)
            except OSError as exc:
                raise DocumentStorageMismatchError() from exc
            for entry in entries:
                portable = relative / entry.name
                key = portable.as_posix().casefold()
                if portable.is_absolute() or ".." in portable.parts or key in seen:
                    raise DocumentStorageMismatchError()
                seen.add(key)
                try:
                    info = entry.stat(follow_symlinks=False)
                except OSError as exc:
                    raise DocumentStorageMismatchError() from exc
                if stat.S_ISLNK(info.st_mode):
                    raise DocumentStorageMismatchError()
                path = Path(entry.path)
                if stat.S_ISDIR(info.st_mode):
                    visit(path, portable)
                elif stat.S_ISREG(info.st_mode) and info.st_nlink == 1:
                    total += info.st_size
                    result.append((portable, path))
                    if len(result) > self.max_files or total > self.max_source_bytes:
                        raise DocumentStorageError(
                            "The document source exceeds the configured safe download limit."
                        )
                else:
                    raise DocumentStorageMismatchError()

        visit(source, PurePosixPath())
        if not any(relative == PurePosixPath("main.tex") for relative, _ in result):
            raise DocumentStorageMismatchError()
        return result

    def _read_main_tex(self, project_id: uuid.UUID) -> bytes:
        files = dict(self._validated_source_files(project_id))
        path = files.get(PurePosixPath("main.tex"))
        if path is None:
            raise DocumentStorageMismatchError()
        self._require_regular(path)
        try:
            return path.read_bytes()
        except OSError as exc:
            raise DocumentStorageMismatchError() from exc

    def _build_source_zip(self, project_id: uuid.UUID) -> bytes:
        files = self._validated_source_files(project_id)
        output = io.BytesIO()
        try:
            with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                for relative, path in files:
                    self._require_regular(path)
                    info = zipfile.ZipInfo(relative.as_posix(), date_time=(1980, 1, 1, 0, 0, 0))
                    info.compress_type = zipfile.ZIP_DEFLATED
                    info.external_attr = 0o600 << 16
                    archive.writestr(info, path.read_bytes())
        except OSError as exc:
            raise DocumentStorageMismatchError() from exc
        return output.getvalue()

    def _quarantine_project(self, project_id: uuid.UUID) -> QuarantinedDocument:
        self._validated_source_files(project_id)
        original = self._project(project_id)
        quarantined = self.root / ".trash" / f"{project_id}-{uuid.uuid4().hex}"
        try:
            os.replace(original, quarantined)
        except OSError as exc:
            raise DocumentStorageError(
                "The document source could not be prepared for safe deletion."
            ) from exc
        return QuarantinedDocument(original=original, quarantined=quarantined)

    def _restore(self, item: QuarantinedDocument) -> None:
        if item.quarantined.exists() and not item.original.exists():
            os.replace(item.quarantined, item.original)

    @staticmethod
    def _purge(item: QuarantinedDocument) -> None:
        if item.quarantined.exists() and not item.quarantined.is_symlink():
            shutil.rmtree(item.quarantined)
