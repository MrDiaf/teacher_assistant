from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import sys
import tarfile
import uuid
from pathlib import Path, PurePosixPath
from typing import BinaryIO

from app.courses.entry import courses_recovery_contribution
from app.documents.entry import documents_recovery_contribution
from app.inbox.entry import inbox_recovery_contribution
from app.platform.recovery import StorageRecoveryContribution

FORMAT_VERSION = 3
DATABASE_FILE = "database.dump"
COURSE_ARCHIVE_FILE = courses_recovery_contribution.archive_file
MAIL_ARCHIVE_FILE = inbox_recovery_contribution.archive_file
DOCUMENT_ARCHIVE_FILE = documents_recovery_contribution.archive_file
MANIFEST_FILE = "manifest.json"
COURSE_ARCHIVE_ROOT = courses_recovery_contribution.archive_root
MAIL_ARCHIVE_ROOT = inbox_recovery_contribution.archive_root
DOCUMENT_ARCHIVE_ROOT = documents_recovery_contribution.archive_root
BUFFER_SIZE = 1024 * 1024
MAX_ARCHIVE_MEMBERS = 100_000
MAX_ARCHIVE_BYTES = 100 * 1024 * 1024 * 1024
MAX_DOCUMENT_ARCHIVE_MEMBERS = documents_recovery_contribution.max_members
MAX_DOCUMENT_ARCHIVE_BYTES = documents_recovery_contribution.max_bytes


class ArchiveValidationError(ValueError):
    """Raised when a backup bundle or private archive is unsafe or inconsistent."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(BUFFER_SIZE):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_source_paths(source: Path, label: str) -> list[Path]:
    paths = [source]
    for path in sorted(source.rglob("*"), key=lambda item: item.as_posix()):
        if path.is_symlink():
            raise ArchiveValidationError(
                f"{label} contains a symbolic link: {path.relative_to(source)}"
            )
        info = path.lstat()
        if not (stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode)):
            raise ArchiveValidationError(
                f"{label} contains an unsupported file type: {path.relative_to(source)}"
            )
        if stat.S_ISREG(info.st_mode) and info.st_nlink != 1:
            raise ArchiveValidationError(
                f"{label} contains a hard-linked file: {path.relative_to(source)}"
            )
        paths.append(path)
    return paths


def create_storage_archive(source: Path, output: BinaryIO, archive_root: str) -> None:
    source = source.resolve()
    if not source.is_dir():
        raise ArchiveValidationError(f"Private storage is not a directory: {source}")
    paths = _safe_source_paths(source, "Private storage")
    with tarfile.open(fileobj=output, mode="w|gz", format=tarfile.PAX_FORMAT) as archive:
        for path in paths:
            relative = path.relative_to(source)
            archive_name = PurePosixPath(archive_root)
            if relative.parts:
                archive_name /= PurePosixPath(*relative.parts)
            archive.add(path, arcname=archive_name.as_posix(), recursive=False)


def create_course_archive(source: Path, output: BinaryIO) -> None:
    create_contributed_archive(courses_recovery_contribution, source, output)


def create_mail_archive(source: Path, output: BinaryIO) -> None:
    create_contributed_archive(inbox_recovery_contribution, source, output)


def create_document_archive(source: Path, output: BinaryIO) -> None:
    create_contributed_archive(documents_recovery_contribution, source, output)


def create_contributed_archive(
    contribution: StorageRecoveryContribution,
    source: Path,
    output: BinaryIO,
) -> None:
    """Create one module archive while Platform owns coordinated timing."""

    create_storage_archive(source, output, contribution.archive_root)


def _validated_members(
    archive: tarfile.TarFile,
    archive_root: str,
    *,
    max_members: int = MAX_ARCHIVE_MEMBERS,
    max_bytes: int = MAX_ARCHIVE_BYTES,
) -> list[tarfile.TarInfo]:
    members = archive.getmembers()
    if not members:
        raise ArchiveValidationError("Private storage archive is empty.")
    if len(members) > max_members:
        raise ArchiveValidationError("Private storage archive contains too many entries.")
    if sum(member.size for member in members if member.isfile()) > max_bytes:
        raise ArchiveValidationError("Private storage archive expands beyond the safe limit.")
    seen: set[str] = set()
    for member in members:
        path = PurePosixPath(member.name)
        if path.is_absolute() or ".." in path.parts:
            raise ArchiveValidationError(f"Unsafe private archive path: {member.name}")
        if not path.parts or path.parts[0] != archive_root:
            raise ArchiveValidationError(
                f"Private archive entry is outside {archive_root}: {member.name}"
            )
        normalized = path.as_posix().rstrip("/").casefold()
        if normalized in seen:
            raise ArchiveValidationError(f"Duplicate private archive path: {member.name}")
        seen.add(normalized)
        if not (member.isdir() or member.isfile()):
            raise ArchiveValidationError(f"Unsupported private archive entry type: {member.name}")
    if archive_root not in seen:
        raise ArchiveValidationError("Private archive root is missing.")
    return members


def verify_storage_archive(path: Path, archive_root: str) -> int:
    try:
        with tarfile.open(path, mode="r:gz") as archive:
            members = _validated_members(archive, archive_root)
            for member in members:
                if not member.isfile():
                    continue
                extracted = archive.extractfile(member)
                if extracted is None:
                    raise ArchiveValidationError(
                        f"Could not read private archive entry: {member.name}"
                    )
                while extracted.read(BUFFER_SIZE):
                    pass
    except (tarfile.TarError, EOFError, OSError) as exc:
        raise ArchiveValidationError(f"Course archive cannot be read: {exc}") from exc
    return sum(member.isfile() for member in members)


def verify_course_archive(path: Path) -> int:
    return verify_storage_archive(path, COURSE_ARCHIVE_ROOT)


def verify_mail_archive(path: Path) -> int:
    return verify_contributed_archive(inbox_recovery_contribution, path)


def verify_document_archive(path: Path) -> int:
    return verify_contributed_archive(documents_recovery_contribution, path)


def verify_contributed_archive(
    contribution: StorageRecoveryContribution,
    path: Path,
) -> int:
    """Verify one contributed archive and return bounded manifest metadata."""

    try:
        with tarfile.open(path, mode="r:gz") as archive:
            members = _validated_members(
                archive,
                contribution.archive_root,
                max_members=contribution.max_members,
                max_bytes=contribution.max_bytes,
            )
            for member in members:
                if member.isfile():
                    extracted = archive.extractfile(member)
                    if extracted is None:
                        raise ArchiveValidationError(
                            f"Could not read document archive entry: {member.name}"
                        )
                    while extracted.read(BUFFER_SIZE):
                        pass
    except (tarfile.TarError, EOFError, OSError) as exc:
        raise ArchiveValidationError(f"Document archive cannot be read: {exc}") from exc
    return sum(member.isfile() for member in members)


def build_manifest(bundle: Path, installation_id: str, created_at: str) -> dict[str, object]:
    database = bundle / DATABASE_FILE
    courses = bundle / COURSE_ARCHIVE_FILE
    mail = bundle / inbox_recovery_contribution.archive_file
    documents = bundle / documents_recovery_contribution.archive_file
    if not all(item.is_file() for item in (database, courses, mail, documents)):
        raise ArchiveValidationError(
            "The database dump and all private storage archives are required."
        )
    file_count = verify_course_archive(courses)
    mail_file_count = verify_mail_archive(mail)
    document_file_count = verify_document_archive(documents)
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
        courses_recovery_contribution.manifest_key: {
            "file": COURSE_ARCHIVE_FILE,
            "root": COURSE_ARCHIVE_ROOT,
            "file_count": file_count,
            "bytes": courses.stat().st_size,
            "sha256": sha256_file(courses),
        },
        inbox_recovery_contribution.manifest_key: {
            "file": inbox_recovery_contribution.archive_file,
            "root": inbox_recovery_contribution.archive_root,
            "file_count": mail_file_count,
            "bytes": mail.stat().st_size,
            "sha256": sha256_file(mail),
        },
        documents_recovery_contribution.manifest_key: {
            "file": documents_recovery_contribution.archive_file,
            "root": documents_recovery_contribution.archive_root,
            "file_count": document_file_count,
            "bytes": documents.stat().st_size,
            "sha256": sha256_file(documents),
        },
        "integration_credentials": {
            "included": False,
            "recovery": "Reconnect the dedicated mailbox after a clean restore.",
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
    if not isinstance(manifest, dict) or manifest.get("format_version") not in {2, FORMAT_VERSION}:
        raise ArchiveValidationError("Backup manifest format is unsupported.")
    format_version = manifest["format_version"]
    installation_id = manifest.get("installation_id")
    if not isinstance(installation_id, str) or not installation_id:
        raise ArchiveValidationError("Backup manifest installation ID is invalid.")
    codex_auth = manifest.get("codex_auth")
    if not isinstance(codex_auth, dict) or codex_auth.get("included") is not False:
        raise ArchiveValidationError("Backup manifest must exclude Codex authentication.")
    integration_credentials = manifest.get("integration_credentials")
    if (
        not isinstance(integration_credentials, dict)
        or integration_credentials.get("included") is not False
    ):
        raise ArchiveValidationError("Backup manifest must exclude integration credentials.")
    database = _manifest_component(bundle, manifest, "database", DATABASE_FILE)
    courses = _manifest_component(
        bundle,
        manifest,
        courses_recovery_contribution.manifest_key,
        courses_recovery_contribution.archive_file,
    )
    mail = _manifest_component(
        bundle,
        manifest,
        inbox_recovery_contribution.manifest_key,
        inbox_recovery_contribution.archive_file,
    )
    documents = (
        _manifest_component(
            bundle,
            manifest,
            documents_recovery_contribution.manifest_key,
            documents_recovery_contribution.archive_file,
        )
        if format_version >= documents_recovery_contribution.introduced_in_format
        else None
    )
    file_count = verify_course_archive(courses)
    course_component = manifest[courses_recovery_contribution.manifest_key]
    assert isinstance(course_component, dict)
    if course_component.get("file_count") != file_count:
        raise ArchiveValidationError("Course archive file count does not match the manifest.")
    mail_file_count = verify_mail_archive(mail)
    mail_component = manifest[inbox_recovery_contribution.manifest_key]
    assert isinstance(mail_component, dict)
    if mail_component.get("file_count") != mail_file_count:
        raise ArchiveValidationError("Mail archive file count does not match the manifest.")
    document_file_count = 0
    if documents is not None:
        document_file_count = verify_document_archive(documents)
        document_component = manifest[documents_recovery_contribution.manifest_key]
        assert isinstance(document_component, dict)
        if document_component.get("file_count") != document_file_count:
            raise ArchiveValidationError("Document archive file count does not match the manifest.")
    return {
        "format_version": format_version,
        "installation_id": installation_id,
        "created_at": manifest.get("created_at"),
        "database": database.name,
        "course_archive": courses.name,
        "course_file_count": file_count,
        "mail_archive": mail.name,
        "mail_file_count": mail_file_count,
        "document_archive": documents.name if documents is not None else None,
        "document_file_count": document_file_count,
    }


def restore_storage_archive(
    archive_path: Path,
    parent: Path,
    directory_name: str,
    rollback_suffix: str,
    archive_root: str,
    max_members: int = MAX_ARCHIVE_MEMBERS,
    max_bytes: int = MAX_ARCHIVE_BYTES,
) -> Path | None:
    if not directory_name or directory_name in {".", ".."} or "/" in directory_name:
        raise ArchiveValidationError("Private storage directory name is unsafe.")
    parent = parent.resolve()
    if not parent.is_dir():
        raise ArchiveValidationError(f"Private storage parent is missing: {parent}")
    target = parent / directory_name
    rollback = parent / f"{directory_name}.before-restore-{rollback_suffix}"
    staging = parent / f".{directory_name}.restore-{uuid.uuid4().hex}"
    if rollback.exists():
        raise ArchiveValidationError(f"Private rollback directory already exists: {rollback}")
    staging.mkdir(mode=0o700)
    try:
        with tarfile.open(archive_path, mode="r:gz") as archive:
            members = _validated_members(
                archive, archive_root, max_members=max_members, max_bytes=max_bytes
            )
            for member in members:
                relative = PurePosixPath(member.name).relative_to(archive_root)
                destination = staging.joinpath(*relative.parts)
                if member.isdir():
                    destination.mkdir(mode=0o700, parents=True, exist_ok=True)
                    continue
                destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                source = archive.extractfile(member)
                if source is None:
                    raise ArchiveValidationError(
                        f"Could not read private archive entry: {member.name}"
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


def restore_empty_storage(parent: Path, directory_name: str, rollback_suffix: str) -> Path | None:
    if not directory_name or directory_name in {".", ".."} or "/" in directory_name:
        raise ArchiveValidationError("Private storage directory name is unsafe.")
    parent = parent.resolve()
    if not parent.is_dir():
        raise ArchiveValidationError(f"Private storage parent is missing: {parent}")
    target = parent / directory_name
    rollback = parent / f"{directory_name}.before-restore-{rollback_suffix}"
    staging = parent / f".{directory_name}.restore-{uuid.uuid4().hex}"
    if rollback.exists():
        raise ArchiveValidationError(f"Private rollback directory already exists: {rollback}")
    staging.mkdir(mode=0o700)
    previous: Path | None = None
    try:
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


def restore_course_archive(
    archive_path: Path, parent: Path, directory_name: str, rollback_suffix: str
) -> Path | None:
    return restore_storage_archive(
        archive_path, parent, directory_name, rollback_suffix, COURSE_ARCHIVE_ROOT
    )


def restore_mail_archive(
    archive_path: Path, parent: Path, directory_name: str, rollback_suffix: str
) -> Path | None:
    return restore_contributed_archive(
        inbox_recovery_contribution,
        archive_path,
        parent,
        directory_name,
        rollback_suffix,
    )


def restore_document_archive(
    archive_path: Path, parent: Path, directory_name: str, rollback_suffix: str
) -> Path | None:
    return restore_contributed_archive(
        documents_recovery_contribution,
        archive_path,
        parent,
        directory_name,
        rollback_suffix,
    )


def restore_contributed_archive(
    contribution: StorageRecoveryContribution,
    archive_path: Path,
    parent: Path,
    directory_name: str,
    rollback_suffix: str,
) -> Path | None:
    """Restore one module archive without owning cross-store rollback order."""

    return restore_storage_archive(
        archive_path,
        parent,
        directory_name,
        rollback_suffix,
        contribution.archive_root,
        contribution.max_members,
        contribution.max_bytes,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Teacher Assistant backup archive helper")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create = subparsers.add_parser("create-course")
    create.add_argument("--source", type=Path, required=True)
    create.add_argument("--output", type=Path)

    create_mail = subparsers.add_parser("create-mail")
    create_mail.add_argument("--source", type=Path, required=True)
    create_mail.add_argument("--output", type=Path)

    create_documents = subparsers.add_parser("create-documents")
    create_documents.add_argument("--source", type=Path, required=True)
    create_documents.add_argument("--output", type=Path)

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
    restore_mail = subparsers.add_parser("restore-mail")
    restore_mail.add_argument("--archive", type=Path, required=True)
    restore_mail.add_argument("--parent", type=Path, required=True)
    restore_mail.add_argument("--directory-name", required=True)
    restore_mail.add_argument("--rollback-suffix", required=True)
    restore_documents = subparsers.add_parser("restore-documents")
    restore_documents.add_argument("--archive", type=Path, required=True)
    restore_documents.add_argument("--parent", type=Path, required=True)
    restore_documents.add_argument("--directory-name", required=True)
    restore_documents.add_argument("--rollback-suffix", required=True)
    restore_empty_documents = subparsers.add_parser("restore-empty-documents")
    restore_empty_documents.add_argument("--parent", type=Path, required=True)
    restore_empty_documents.add_argument("--directory-name", required=True)
    restore_empty_documents.add_argument("--rollback-suffix", required=True)
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
        elif args.command == "create-mail":
            if args.output is None:
                create_mail_archive(args.source, sys.stdout.buffer)
            else:
                with args.output.open("xb") as output:
                    create_mail_archive(args.source, output)
        elif args.command == "create-documents":
            if args.output is None:
                create_document_archive(args.source, sys.stdout.buffer)
            else:
                with args.output.open("xb") as output:
                    create_document_archive(args.source, output)
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
        elif args.command == "restore-mail":
            previous = restore_mail_archive(
                args.archive,
                args.parent,
                args.directory_name,
                args.rollback_suffix,
            )
            print(previous or "none")
        elif args.command == "restore-documents":
            previous = restore_document_archive(
                args.archive,
                args.parent,
                args.directory_name,
                args.rollback_suffix,
            )
            print(previous or "none")
        elif args.command == "restore-empty-documents":
            previous = restore_empty_storage(
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
