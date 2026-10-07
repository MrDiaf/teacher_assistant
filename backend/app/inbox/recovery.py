"""Inbox-owned declaration for coordinated attachment recovery."""

from app.platform.recovery import StorageRecoveryContribution

inbox_recovery_contribution = StorageRecoveryContribution(
    id="inbox",
    manifest_key="mail_files",
    archive_file="mail-attachments.tar.gz",
    archive_root="mail_attachments",
    introduced_in_format=1,
    max_members=100_000,
    max_bytes=100 * 1024 * 1024 * 1024,
)
