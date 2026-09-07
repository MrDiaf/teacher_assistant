from __future__ import annotations

import io
import json
import tarfile
from pathlib import Path

import pytest

from app.maintenance.data_archive import (
    ArchiveValidationError,
    build_manifest,
    create_course_archive,
    create_mail_archive,
    restore_course_archive,
    restore_mail_archive,
    verify_bundle,
    verify_course_archive,
    verify_mail_archive,
)


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
