from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tarfile
import uuid
from pathlib import Path, PurePosixPath
from typing import BinaryIO

FORMAT_VERSION = 1
DATABASE_FILE = "database.dump"
COURSE_ARCHIVE_FILE = "course-content.tar.gz"
MANIFEST_FILE = "manifest.json"
COURSE_ARCHIVE_ROOT = "course_content"
BUFFER_SIZE = 1024 * 1024


class ArchiveValidationError(ValueError):
    """Raised when a backup bundle or course archive is unsafe or inconsistent."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(BUFFER_SIZE):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_source_paths(source: Path) -> list[Path]:
    paths = [source]
    for path in sorted(source.rglob("*"), key=lambda item: item.as_posix()):
        if path.is_symlink():
            raise ArchiveValidationError(
                f"Course storage contains a symbolic link: {path.relative_to(source)}"
            )
        if not (path.is_dir() or path.is_file()):
            raise ArchiveValidationError(
                f"Course storage contains an unsupported file type: {path.relative_to(source)}"
            )
        paths.append(path)
    return paths


def create_course_archive(source: Path, output: BinaryIO) -> None:
    source = source.resolve()
    if not source.is_dir():
        raise ArchiveValidationError(f"Course storage is not a directory: {source}")
    paths = _safe_source_paths(source)
    with tarfile.open(fileobj=output, mode="w|gz", format=tarfile.PAX_FORMAT) as archive:
        for path in paths:
            relative = path.relative_to(source)
            archive_name = PurePosixPath(COURSE_ARCHIVE_ROOT)
            if relative.parts:
                archive_name /= PurePosixPath(*relative.parts)
            archive.add(path, arcname=archive_name.as_posix(), recursive=False)


def _validated_members(archive: tarfile.TarFile) -> list[tarfile.TarInfo]:
    members = archive.getmembers()
    if not members:
        raise ArchiveValidationError("Course archive is empty.")
    seen: set[str] = set()
    for member in members:
        path = PurePosixPath(member.name)
        if path.is_absolute() or ".." in path.parts:
            raise ArchiveValidationError(f"Unsafe course archive path: {member.name}")
        if not path.parts or path.parts[0] != COURSE_ARCHIVE_ROOT:
            raise ArchiveValidationError(
                f"Course archive entry is outside {COURSE_ARCHIVE_ROOT}: {member.name}"
            )
        normalized = path.as_posix().rstrip("/")
        if normalized in seen:
            raise ArchiveValidationError(f"Duplicate course archive path: {member.name}")
        seen.add(normalized)
        if not (member.isdir() or member.isfile()):
            raise ArchiveValidationError(
                f"Unsupported course archive entry type: {member.name}"
            )
    if COURSE_ARCHIVE_ROOT not in seen:
        raise ArchiveValidationError("Course archive root is missing.")
    return members


def verify_course_archive(path: Path) -> int:
    try:
        with tarfile.open(path, mode="r:gz") as archive:
            members = _validated_members(archive)
            for member in members:
                if not member.isfile():
                    continue
                extracted = archive.extractfile(member)
                if extracted is None:
                    raise ArchiveValidationError(
                        f"Could not read course archive entry: {member.name}"
                    )
                while extracted.read(BUFFER_SIZE):
                    pass
    except (tarfile.TarError, EOFError, OSError) as exc:
        raise ArchiveValidationError(f"Course archive cannot be read: {exc}") from exc
    return sum(member.isfile() for member in members)


def build_manifest(bundle: Path, installation_id: str, created_at: str) -> dict[str, object]:
    database = bundle / DATABASE_FILE
    courses = bundle / COURSE_ARCHIVE_FILE
    if not database.is_file() or not courses.is_file():
        raise ArchiveValidationError("The database dump and course archive are both required.")
    file_count = verify_course_archive(courses)
    return {
        "format_version": FORMAT_VERSION,
        "created_at": created_at,
        "installation_id": installation_id,
        "database": {
            "file": DATABASE_FILE,
            "format": "postgresql-custom",
            "bytes": database.stat().st_size,
            "sha256": sha256_file(database),
        },
        "course_files": {
            "file": COURSE_ARCHIVE_FILE,
            "root": COURSE_ARCHIVE_ROOT,
            "file_count": file_count,
            "bytes": courses.stat().st_size,
            "sha256": sha256_file(courses),
        },
        "codex_auth": {
            "included": False,
            "recovery": "Sign in with ChatGPT again if this installation has no renewable session.",
        },
    }


def _manifest_component(
    bundle: Path, manifest: dict[str, object], key: str, expected_file: str
) -> Path:
    component = manifest.get(key)
    if not isinstance(component, dict):
        raise ArchiveValidationError(f"Manifest field {key} is missing or invalid.")
    file_name = component.get("file")
    if file_name != expected_file:
        raise ArchiveValidationError(f"Manifest field {key}.file is invalid.")
    path = bundle / expected_file
    if not path.is_file():
        raise ArchiveValidationError(f"Backup component is missing: {expected_file}")
    expected_size = component.get("bytes")
    if not isinstance(expected_size, int) or expected_size != path.stat().st_size:
        raise ArchiveValidationError(f"Backup size does not match the manifest: {expected_file}")
    expected_digest = component.get("sha256")
    if not isinstance(expected_digest, str) or expected_digest != sha256_file(path):
        raise ArchiveValidationError(
            f"Backup checksum does not match the manifest: {expected_file}"
        )
    return path


def verify_bundle(bundle: Path) -> dict[str, object]:
    bundle = bundle.resolve()
    manifest_path = bundle / MANIFEST_FILE
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ArchiveValidationError(f"Backup manifest cannot be read: {exc}") from exc
    if not isinstance(manifest, dict) or manifest.get("format_version") != FORMAT_VERSION:
        raise ArchiveValidationError("Backup manifest format is unsupported.")
    installation_id = manifest.get("installation_id")
    if not isinstance(installation_id, str) or not installation_id:
        raise ArchiveValidationError("Backup manifest installation ID is invalid.")
    codex_auth = manifest.get("codex_auth")
    if not isinstance(codex_auth, dict) or codex_auth.get("included") is not False:
        raise ArchiveValidationError("Backup manifest must exclude Codex authentication.")
    database = _manifest_component(bundle, manifest, "database", DATABASE_FILE)
    courses = _manifest_component(bundle, manifest, "course_files", COURSE_ARCHIVE_FILE)
    file_count = verify_course_archive(courses)
    course_component = manifest["course_files"]
    assert isinstance(course_component, dict)
    if course_component.get("file_count") != file_count:
        raise ArchiveValidationError("Course archive file count does not match the manifest.")
    return {
        "installation_id": installation_id,
        "created_at": manifest.get("created_at"),
        "database": database.name,
        "course_archive": courses.name,
        "course_file_count": file_count,
    }


def restore_course_archive(
    archive_path: Path,
    parent: Path,
    directory_name: str,
    rollback_suffix: str,
) -> Path | None:
    if not directory_name or directory_name in {".", ".."} or "/" in directory_name:
        raise ArchiveValidationError("Course storage directory name is unsafe.")
    parent = parent.resolve()
    if not parent.is_dir():
        raise ArchiveValidationError(f"Course storage parent is missing: {parent}")
    target = parent / directory_name
    rollback = parent / f"{directory_name}.before-restore-{rollback_suffix}"
    staging = parent / f".{directory_name}.restore-{uuid.uuid4().hex}"
    if rollback.exists():
        raise ArchiveValidationError(f"Course rollback directory already exists: {rollback}")
    staging.mkdir(mode=0o700)
    try:
        with tarfile.open(archive_path, mode="r:gz") as archive:
            members = _validated_members(archive)
            for member in members:
                relative = PurePosixPath(member.name).relative_to(COURSE_ARCHIVE_ROOT)
                destination = staging.joinpath(*relative.parts)
                if member.isdir():
                    destination.mkdir(mode=0o700, parents=True, exist_ok=True)
                    continue
                destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                source = archive.extractfile(member)
                if source is None:
                    raise ArchiveValidationError(
                        f"Could not read course archive entry: {member.name}"
                    )
                with destination.open("xb") as output:
                    shutil.copyfileobj(source, output, length=BUFFER_SIZE)
                destination.chmod(0o600)
        previous: Path | None = None
        if target.exists():
            os.replace(target, rollback)
            previous = rollback
        try:
            os.replace(staging, target)
        except Exception:
            if previous is not None and not target.exists():
                os.replace(previous, target)
            raise
        return previous
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Teacher Assistant backup archive helper")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create = subparsers.add_parser("create-course")
    create.add_argument("--source", type=Path, required=True)
    create.add_argument("--output", type=Path)

    manifest = subparsers.add_parser("create-manifest")
    manifest.add_argument("--bundle", type=Path, required=True)
    manifest.add_argument("--installation-id", required=True)
    manifest.add_argument("--created-at", required=True)

    verify = subparsers.add_parser("verify-bundle")
    verify.add_argument("--bundle", type=Path, required=True)

    restore = subparsers.add_parser("restore-course")
    restore.add_argument("--archive", type=Path, required=True)
    restore.add_argument("--parent", type=Path, required=True)
    restore.add_argument("--directory-name", required=True)
    restore.add_argument("--rollback-suffix", required=True)
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        if args.command == "create-course":
            if args.output is None:
                create_course_archive(args.source, sys.stdout.buffer)
            else:
                with args.output.open("xb") as output:
                    create_course_archive(args.source, output)
        elif args.command == "create-manifest":
            manifest = build_manifest(args.bundle, args.installation_id, args.created_at)
            json.dump(manifest, sys.stdout, indent=2, sort_keys=True)
            sys.stdout.write("\n")
        elif args.command == "verify-bundle":
            json.dump(verify_bundle(args.bundle), sys.stdout, sort_keys=True)
            sys.stdout.write("\n")
        elif args.command == "restore-course":
            previous = restore_course_archive(
                args.archive,
                args.parent,
                args.directory_name,
                args.rollback_suffix,
            )
            print(previous or "none")
        return 0
    except ArchiveValidationError as exc:
        print(f"Backup validation failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
