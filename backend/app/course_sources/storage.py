from __future__ import annotations

import hashlib
import os
import re
import shutil
import unicodedata
import uuid
import zipfile
from collections.abc import AsyncIterable
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING

from starlette.concurrency import run_in_threadpool

from app.core.errors import (
    CourseSourceFileTooLargeError,
    CourseSourceStorageError,
    InvalidCourseSourceFileError,
)
from app.course_sources.extraction import (
    PDF_MIME_TYPE,
    PPTX_MIME_TYPE,
)
from app.course_sources.models import CourseSourceType

if TYPE_CHECKING:
    from app.course_sources.models import CourseSource

SAFE_FILENAME_PATTERN = re.compile(r"[^A-Za-z0-9._() -]+")
SAFE_EXTENSION_PATTERN = re.compile(r"^\.[a-z0-9]{1,10}$")
FORMAT_BY_EXTENSION = {
    ".pdf": (".pdf", PDF_MIME_TYPE),
    ".pptx": (".pptx", PPTX_MIME_TYPE),
    ".txt": (".txt", "text/plain"),
    ".md": (".md", "text/markdown"),
    ".markdown": (".md", "text/markdown"),
}


class StoredCourseFileMissingError(Exception):
    pass


@dataclass(frozen=True)
class StoredUpload:
    source_id: uuid.UUID
    original_filename: str
    stored_filename: str
    mime_type: str
    file_size: int
    storage_path: str
    absolute_path: Path
    content_hash: str


@dataclass(frozen=True)
class QuarantinedPath:
    original: Path
    quarantined: Path


class CourseStorage:
    def __init__(self, root: Path, maximum_bytes: int, maximum_mb: int) -> None:
        self.root = root.resolve()
        self.maximum_bytes = maximum_bytes
        self.maximum_mb = maximum_mb

    async def store(
        self,
        *,
        course_id: uuid.UUID,
        source_id: uuid.UUID,
        source_type: CourseSourceType,
        file_name: str,
        chunks: AsyncIterable[bytes],
        content_length: int | None,
    ) -> StoredUpload:
        original_filename = self.sanitize_filename(file_name)
        if content_length is not None and content_length > self.maximum_bytes:
            raise CourseSourceFileTooLargeError(self.maximum_mb)
        stored_filename, mime_type = self._storage_identity(original_filename)
        relative_path = self.expected_relative_path(
            course_id,
            source_id,
            source_type,
            stored_filename,
        )
        final_path = self._absolute_path(relative_path)
        temporary_path = self._absolute_path(
            PurePosixPath(".uploads", f"{source_id}.upload")
        )
        await run_in_threadpool(temporary_path.parent.mkdir, parents=True, exist_ok=True)
        await run_in_threadpool(final_path.parent.mkdir, parents=True, exist_ok=False)

        size = 0
        digest = hashlib.sha256()
        handle = await run_in_threadpool(temporary_path.open, "xb")
        try:
            async for chunk in chunks:
                if not chunk:
                    continue
                size += len(chunk)
                if size > self.maximum_bytes:
                    raise CourseSourceFileTooLargeError(self.maximum_mb)
                digest.update(chunk)
                await run_in_threadpool(handle.write, chunk)
        except Exception:
            await run_in_threadpool(handle.close)
            await self._remove_path(temporary_path)
            await self._remove_empty_source_directory(final_path.parent)
            raise
        else:
            await run_in_threadpool(handle.close)

        if size == 0:
            await self._remove_path(temporary_path)
            await self._remove_empty_source_directory(final_path.parent)
            raise InvalidCourseSourceFileError("The uploaded course file is empty.")

        try:
            await run_in_threadpool(self._validate_file, temporary_path, mime_type)
            await run_in_threadpool(os.chmod, temporary_path, 0o600)
            await run_in_threadpool(os.replace, temporary_path, final_path)
        except InvalidCourseSourceFileError:
            await self._remove_path(temporary_path)
            await self._remove_empty_source_directory(final_path.parent)
            raise
        except Exception as exc:
            await self._remove_path(temporary_path)
            await self._remove_empty_source_directory(final_path.parent)
            raise CourseSourceStorageError() from exc

        return StoredUpload(
            source_id=source_id,
            original_filename=original_filename,
            stored_filename=stored_filename,
            mime_type=mime_type,
            file_size=size,
            storage_path=relative_path.as_posix(),
            absolute_path=final_path,
            content_hash=digest.hexdigest(),
        )

    async def resolve_source_file(self, source: CourseSource) -> Path:
        expected = self.expected_relative_path(
            source.course_id,
            source.id,
            source.source_type,
            source.stored_filename,
        )
        if PurePosixPath(source.storage_path) != expected:
            raise CourseSourceStorageError(
                "The stored course file metadata failed an integrity check."
            )
        path = self._absolute_path(expected)
        if not await run_in_threadpool(path.is_file):
            raise StoredCourseFileMissingError(
                "The stored file is missing. Delete this record and upload the file again."
            )
        return path

    async def quarantine_source(
        self,
        source: CourseSource,
    ) -> QuarantinedPath | None:
        expected = self.expected_relative_path(
            source.course_id,
            source.id,
            source.source_type,
            source.stored_filename,
        )
        if PurePosixPath(source.storage_path) != expected:
            raise CourseSourceStorageError(
                "The stored course file metadata failed an integrity check."
            )
        source_directory = self._absolute_path(expected.parent)
        return await self._quarantine(source_directory)

    async def quarantine_course(
        self,
        course_id: uuid.UUID,
    ) -> QuarantinedPath | None:
        return await self._quarantine(self._absolute_path(PurePosixPath(str(course_id))))

    async def restore(self, quarantine: QuarantinedPath | None) -> None:
        if quarantine is None or not await run_in_threadpool(
            quarantine.quarantined.exists
        ):
            return
        await run_in_threadpool(
            quarantine.original.parent.mkdir,
            parents=True,
            exist_ok=True,
        )
        await run_in_threadpool(
            os.replace,
            quarantine.quarantined,
            quarantine.original,
        )

    async def purge(self, quarantine: QuarantinedPath | None) -> None:
        if quarantine is not None:
            await self._remove_path(quarantine.quarantined)

    async def remove_source_directory(
        self,
        course_id: uuid.UUID,
        source_type: CourseSourceType,
        source_id: uuid.UUID,
    ) -> None:
        directory = self._absolute_path(
            PurePosixPath(str(course_id), source_type.value, str(source_id))
        )
        await self._remove_path(directory)

    async def _quarantine(self, path: Path) -> QuarantinedPath | None:
        if not await run_in_threadpool(path.exists):
            return None
        trash = self._absolute_path(PurePosixPath(".trash", str(uuid.uuid4())))
        try:
            await run_in_threadpool(trash.parent.mkdir, parents=True, exist_ok=True)
            await run_in_threadpool(os.replace, path, trash)
        except Exception as exc:
            raise CourseSourceStorageError(
                "The course file could not be prepared for safe deletion."
            ) from exc
        return QuarantinedPath(original=path, quarantined=trash)

    async def _remove_path(self, path: Path) -> None:
        if not await run_in_threadpool(path.exists):
            return
        if await run_in_threadpool(path.is_dir):
            await run_in_threadpool(shutil.rmtree, path)
        else:
            await run_in_threadpool(path.unlink)

    async def _remove_empty_source_directory(self, directory: Path) -> None:
        try:
            await run_in_threadpool(directory.rmdir)
        except OSError:
            pass

    def _absolute_path(self, relative_path: PurePosixPath) -> Path:
        if relative_path.is_absolute() or ".." in relative_path.parts:
            raise CourseSourceStorageError(
                "The course storage path failed an integrity check."
            )
        path = self.root.joinpath(*relative_path.parts).resolve()
        if not path.is_relative_to(self.root):
            raise CourseSourceStorageError(
                "The course storage path failed an integrity check."
            )
        return path

    @staticmethod
    def expected_relative_path(
        course_id: uuid.UUID,
        source_id: uuid.UUID,
        source_type: CourseSourceType,
        stored_filename: str,
    ) -> PurePosixPath:
        return PurePosixPath(
            str(course_id),
            source_type.value,
            str(source_id),
            stored_filename,
        )

    @staticmethod
    def sanitize_filename(file_name: str) -> str:
        normalized = unicodedata.normalize("NFKC", file_name).strip()
        if (
            not normalized
            or normalized in {".", ".."}
            or "/" in normalized
            or "\\" in normalized
        ):
            raise InvalidCourseSourceFileError(
                "The uploaded filename contains an invalid path."
            )
        if any(ord(character) < 32 for character in normalized):
            raise InvalidCourseSourceFileError(
                "The uploaded filename contains invalid characters."
            )
        safe_name = SAFE_FILENAME_PATTERN.sub("_", normalized).strip(" .")
        if not safe_name:
            raise InvalidCourseSourceFileError("The uploaded filename is not valid.")
        if len(safe_name) > 255:
            suffix = Path(safe_name).suffix[-11:]
            safe_name = f"{safe_name[: 255 - len(suffix)]}{suffix}"
        return safe_name

    @staticmethod
    def _storage_identity(file_name: str) -> tuple[str, str]:
        extension = Path(file_name).suffix.lower()
        supported = FORMAT_BY_EXTENSION.get(extension)
        if supported is not None:
            stored_extension, mime_type = supported
            return f"original{stored_extension}", mime_type
        stored_extension = extension if SAFE_EXTENSION_PATTERN.fullmatch(extension) else ".bin"
        return f"original{stored_extension}", "application/octet-stream"

    @staticmethod
    def _validate_file(path: Path, mime_type: str) -> None:
        if mime_type == PDF_MIME_TYPE:
            with path.open("rb") as uploaded:
                if b"%PDF-" not in uploaded.read(1024):
                    raise InvalidCourseSourceFileError(
                        "The file extension is PDF, but its contents are not a PDF."
                    )
        elif mime_type == PPTX_MIME_TYPE:
            try:
                with zipfile.ZipFile(path) as archive:
                    names = set(archive.namelist())
                    if (
                        "[Content_Types].xml" not in names
                        or "ppt/presentation.xml" not in names
                        or len(names) > 10_000
                        or sum(item.file_size for item in archive.infolist())
                        > 200 * 1024 * 1024
                    ):
                        raise InvalidCourseSourceFileError(
                            "The file extension is PPTX, but its contents are not a "
                            "supported PowerPoint presentation."
                        )
            except zipfile.BadZipFile as exc:
                raise InvalidCourseSourceFileError(
                    "The file extension is PPTX, but its contents are not a "
                    "PowerPoint presentation."
                ) from exc
        elif mime_type in {"text/plain", "text/markdown"}:
            with path.open("rb") as uploaded:
                sample = uploaded.read(8192)
            if b"\x00" in sample:
                raise InvalidCourseSourceFileError(
                    "The file extension indicates text, but the file contains binary data."
                )
            try:
                sample.decode("utf-8-sig")
            except UnicodeDecodeError as exc:
                raise InvalidCourseSourceFileError(
                    "Text and Markdown files must use UTF-8 encoding."
                ) from exc
