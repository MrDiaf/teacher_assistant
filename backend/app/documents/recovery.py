"""Documents-owned declaration for coordinated source recovery."""

from app.platform.recovery import StorageRecoveryContribution

DOCUMENT_ARCHIVE_FILE = "document-projects.tar.gz"
DOCUMENT_ARCHIVE_ROOT = "document_projects"
MAX_DOCUMENT_ARCHIVE_MEMBERS = 100_000
MAX_DOCUMENT_ARCHIVE_BYTES = 100 * 1024 * 1024 * 1024

documents_recovery_contribution = StorageRecoveryContribution(
    id="documents",
    manifest_key="document_files",
    archive_file=DOCUMENT_ARCHIVE_FILE,
    archive_root=DOCUMENT_ARCHIVE_ROOT,
    introduced_in_format=3,
    max_members=MAX_DOCUMENT_ARCHIVE_MEMBERS,
    max_bytes=MAX_DOCUMENT_ARCHIVE_BYTES,
)
