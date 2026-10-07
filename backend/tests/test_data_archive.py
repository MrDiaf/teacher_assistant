from __future__ import annotations

import io
import json
import os
import tarfile
from dataclasses import fields
from pathlib import Path

import pytest

from app.courses.entry import courses_recovery_contribution
from app.documents.entry import documents_recovery_contribution
from app.inbox.entry import inbox_recovery_contribution
from app.maintenance.data_archive import (
    ArchiveValidationError,
    build_manifest,
    create_contributed_archive,
    create_course_archive,
    create_document_archive,
    create_mail_archive,
    restore_contributed_archive,
    restore_course_archive,
    restore_document_archive,
    restore_empty_storage,
    restore_mail_archive,
    verify_bundle,
    verify_contributed_archive,
    verify_course_archive,
    verify_document_archive,
    verify_mail_archive,
)
from app.platform.recovery import RecoveryContributionError, StorageRecoveryContribution


def create_bundle(tmp_path: Path) -> tuple[Path, Path]:
    source = tmp_path / "source"
    upload = source / "course-id" / "slides" / "source-id" / "original.pdf"
    upload.parent.mkdir(parents=True)
    upload.write_bytes(b"fixture-pdf")
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    (bundle / "database.dump").write_bytes(b"fixture-postgres-custom-dump")
    archive = bundle / "course-content.tar.gz"
    with archive.open("wb") as output:
        create_course_archive(source, output)
    mail_source = tmp_path / "mail-source"
    mail_attachment = mail_source / "message-id" / "attachment-id.bin"
    mail_attachment.parent.mkdir(parents=True)
    mail_attachment.write_bytes(b"private-mail-attachment")
    mail_archive = bundle / "mail-attachments.tar.gz"
    with mail_archive.open("wb") as output:
        create_mail_archive(mail_source, output)
    document_source = tmp_path / "document-source"
    main_tex = document_source / "project-id" / "source" / "main.tex"
    main_tex.parent.mkdir(parents=True)
    main_tex.write_text("private latex source", encoding="utf-8")
    (main_tex.parents[1] / "build").mkdir()
    document_archive = bundle / "document-projects.tar.gz"
    with document_archive.open("wb") as output:
        create_document_archive(document_source, output)
    manifest = build_manifest(bundle, "fixture-installation", "20260831T120000Z")
    (bundle / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return bundle, upload


def test_bundle_manifest_verifies_database_and_course_checksums(tmp_path: Path) -> None:
    bundle, _ = create_bundle(tmp_path)

    verified = verify_bundle(bundle)

    assert verified["installation_id"] == "fixture-installation"
    assert verified["course_file_count"] == 1
    assert verified["mail_file_count"] == 1
    assert verified["mail_archive"] == "mail-attachments.tar.gz"
    assert verified["document_file_count"] == 1
    assert verified["document_archive"] == "document-projects.tar.gz"


def test_courses_recovery_contribution_preserves_established_storage_identities() -> None:
    # These identities predate the contribution; existing backups depend on them.
    assert courses_recovery_contribution == StorageRecoveryContribution(
        id="courses",
        manifest_key="course_files",
        archive_file="course-content.tar.gz",
        archive_root="course_content",
        introduced_in_format=1,
        max_members=100_000,
        max_bytes=100 * 1024 * 1024 * 1024,
    )


def test_documents_recovery_contribution_preserves_bounded_storage_identities() -> None:
    assert documents_recovery_contribution == StorageRecoveryContribution(
        id="documents",
        manifest_key="document_files",
        archive_file="document-projects.tar.gz",
        archive_root="document_projects",
        introduced_in_format=3,
        max_members=100_000,
        max_bytes=100 * 1024 * 1024 * 1024,
    )
    assert {field.name for field in fields(StorageRecoveryContribution)} == {
        "id",
        "manifest_key",
        "archive_file",
        "archive_root",
        "introduced_in_format",
        "max_members",
        "max_bytes",
    }


def test_inbox_recovery_contribution_preserves_attachments_and_excludes_credentials(
    tmp_path: Path,
) -> None:
    assert inbox_recovery_contribution == StorageRecoveryContribution(
        id="inbox",
        manifest_key="mail_files",
        archive_file="mail-attachments.tar.gz",
        archive_root="mail_attachments",
        introduced_in_format=1,
        max_members=100_000,
        max_bytes=100 * 1024 * 1024 * 1024,
    )

    bundle, _ = create_bundle(tmp_path)
    manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["integration_credentials"] == {
        "included": False,
        "recovery": "Reconnect the dedicated mailbox after a clean restore.",
    }


@pytest.mark.parametrize(
    ("override", "message"),
    [
        ({"id": "../documents"}, "id"),
        ({"manifest_key": "document/files"}, "manifest key"),
        ({"archive_file": "../documents.tar.gz"}, "archive file"),
        ({"archive_root": "/document_projects"}, "archive root"),
        ({"introduced_in_format": 0}, "format version"),
        ({"max_members": 0}, "member limit"),
        ({"max_bytes": True}, "byte limit"),
    ],
)
def test_recovery_contribution_rejects_unsafe_or_unbounded_values(
    override: dict[str, object], message: str
) -> None:
    values: dict[str, object] = {
        "id": "documents",
        "manifest_key": "document_files",
        "archive_file": "document-projects.tar.gz",
        "archive_root": "document_projects",
        "introduced_in_format": 3,
        "max_members": 100,
        "max_bytes": 1024,
    }
    values.update(override)

    with pytest.raises(RecoveryContributionError, match=message):
        StorageRecoveryContribution(**values)  # type: ignore[arg-type]


def test_bundle_verification_accepts_pre_documents_format_two_backup(tmp_path: Path) -> None:
    bundle, _ = create_bundle(tmp_path)
    manifest_path = bundle / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["format_version"] = 2
    manifest.pop("document_files")
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with_unmanifested_archive = verify_bundle(bundle)
    assert with_unmanifested_archive["document_archive"] is None

    (bundle / "document-projects.tar.gz").unlink()

    verified = verify_bundle(bundle)

    assert verified["format_version"] == 2
    assert verified["document_archive"] is None
    assert verified["document_file_count"] == 0


def test_bundle_verification_rejects_corrupt_component(tmp_path: Path) -> None:
    bundle, _ = create_bundle(tmp_path)
    with (bundle / "course-content.tar.gz").open("ab") as output:
        output.write(b"corrupt")

    with pytest.raises(ArchiveValidationError, match="manifest"):
        verify_bundle(bundle)


def test_course_archive_rejects_path_traversal(tmp_path: Path) -> None:
    archive_path = tmp_path / "unsafe.tar.gz"
    with tarfile.open(archive_path, "w:gz") as archive:
        root = tarfile.TarInfo("course_content")
        root.type = tarfile.DIRTYPE
        archive.addfile(root)
        unsafe = tarfile.TarInfo("course_content/../../outside.txt")
        unsafe.size = 4
        archive.addfile(unsafe, io.BytesIO(b"nope"))

    with pytest.raises(ArchiveValidationError, match="Unsafe"):
        verify_course_archive(archive_path)


def test_mail_archive_round_trip_and_rejects_path_traversal(tmp_path: Path) -> None:
    source = tmp_path / "mail"
    stored = source / "message" / "attachment.bin"
    stored.parent.mkdir(parents=True)
    stored.write_bytes(b"mail bytes")
    archive_path = tmp_path / "mail.tar.gz"
    with archive_path.open("wb") as output:
        create_mail_archive(source, output)
    assert verify_mail_archive(archive_path) == 1

    parent = tmp_path / "restore"
    parent.mkdir()
    restore_mail_archive(archive_path, parent, "mail", "fixture")
    assert (parent / "mail" / "message" / "attachment.bin").read_bytes() == b"mail bytes"


def test_document_archive_round_trip_and_rejects_special_entries(tmp_path: Path) -> None:
    source = tmp_path / "documents"
    main = source / "project" / "source" / "main.tex"
    main.parent.mkdir(parents=True)
    main.write_text("source", encoding="utf-8")
    archive_path = tmp_path / "documents.tar.gz"
    with archive_path.open("wb") as output:
        create_contributed_archive(documents_recovery_contribution, source, output)
    assert verify_contributed_archive(documents_recovery_contribution, archive_path) == 1

    parent = tmp_path / "restore-documents"
    parent.mkdir()
    restore_contributed_archive(
        documents_recovery_contribution,
        archive_path,
        parent,
        "documents",
        "fixture",
    )
    assert (parent / "documents" / "project" / "source" / "main.tex").read_text() == "source"

    unsafe = tmp_path / "unsafe-documents.tar.gz"
    with tarfile.open(unsafe, "w:gz") as archive:
        root = tarfile.TarInfo("document_projects")
        root.type = tarfile.DIRTYPE
        archive.addfile(root)
        link = tarfile.TarInfo("document_projects/link")
        link.type = tarfile.SYMTYPE
        link.linkname = "/etc/passwd"
        archive.addfile(link)
    with pytest.raises(ArchiveValidationError, match="Unsupported"):
        verify_document_archive(unsafe)


def test_document_restore_recovers_previous_tree_when_publish_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source-documents"
    main = source / "project" / "source" / "main.tex"
    main.parent.mkdir(parents=True)
    main.write_text("restored source", encoding="utf-8")
    archive_path = tmp_path / "documents.tar.gz"
    with archive_path.open("wb") as output:
        create_document_archive(source, output)

    parent = tmp_path / "restore-documents"
    target = parent / "documents"
    target.mkdir(parents=True)
    old = target / "old.tex"
    old.write_text("old source", encoding="utf-8")
    real_replace = os.replace

    def fail_staging_publish(source_path: Path, destination_path: Path) -> None:
        if source_path.name.startswith(".documents.restore-") and destination_path == target:
            raise OSError("fixture publish failure")
        real_replace(source_path, destination_path)

    monkeypatch.setattr("app.maintenance.data_archive.os.replace", fail_staging_publish)

    with pytest.raises(OSError, match="fixture publish failure"):
        restore_document_archive(archive_path, parent, "documents", "fixture")

    assert old.read_text(encoding="utf-8") == "old source"
    assert not (parent / "documents.before-restore-fixture").exists()
    assert not list(parent.glob(".documents.restore-*"))


def test_restore_keeps_previous_course_tree_as_rollback(tmp_path: Path) -> None:
    bundle, upload = create_bundle(tmp_path)
    parent = tmp_path / "restore-parent"
    target = parent / "course_content"
    target.mkdir(parents=True)
    (target / "old.txt").write_text("old", encoding="utf-8")

    rollback = restore_course_archive(
        bundle / "course-content.tar.gz",
        parent,
        "course_content",
        "fixture",
    )

    assert rollback == parent / "course_content.before-restore-fixture"
    assert (rollback / "old.txt").read_text(encoding="utf-8") == "old"
    restored = target / upload.relative_to(tmp_path / "source")
    assert restored.read_bytes() == b"fixture-pdf"
    assert restored.stat().st_mode & 0o777 == 0o600


def test_restore_refuses_to_overwrite_existing_rollback(tmp_path: Path) -> None:
    bundle, _ = create_bundle(tmp_path)
    parent = tmp_path / "restore-parent"
    (parent / "course_content").mkdir(parents=True)
    (parent / "course_content.before-restore-fixture").mkdir()

    with pytest.raises(ArchiveValidationError, match="already exists"):
        restore_course_archive(
            bundle / "course-content.tar.gz",
            parent,
            "course_content",
            "fixture",
        )


def test_empty_storage_restore_preserves_previous_tree_as_rollback(tmp_path: Path) -> None:
    parent = tmp_path / "restore-parent"
    target = parent / "document_projects"
    target.mkdir(parents=True)
    (target / "old.tex").write_text("old source", encoding="utf-8")

    rollback = restore_empty_storage(parent, "document_projects", "fixture")

    assert rollback == parent / "document_projects.before-restore-fixture"
    assert (rollback / "old.tex").read_text(encoding="utf-8") == "old source"
    assert target.is_dir()
    assert list(target.iterdir()) == []
    assert target.stat().st_mode & 0o077 == 0
