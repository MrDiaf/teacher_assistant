"""Courses-owned declaration for coordinated course-content recovery."""

from app.platform.recovery import StorageRecoveryContribution

COURSE_ARCHIVE_FILE = "course-content.tar.gz"
COURSE_ARCHIVE_ROOT = "course_content"
MAX_COURSE_ARCHIVE_MEMBERS = 100_000
MAX_COURSE_ARCHIVE_BYTES = 100 * 1024 * 1024 * 1024

courses_recovery_contribution = StorageRecoveryContribution(
    id="courses",
    manifest_key="course_files",
    archive_file=COURSE_ARCHIVE_FILE,
    archive_root=COURSE_ARCHIVE_ROOT,
    introduced_in_format=1,
    max_members=MAX_COURSE_ARCHIVE_MEMBERS,
    max_bytes=MAX_COURSE_ARCHIVE_BYTES,
)
