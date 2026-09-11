"""Typed declarations consumed by Platform's coordinated recovery flow."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import PurePosixPath

_CONTRIBUTION_ID = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
_MANIFEST_KEY = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")


class RecoveryContributionError(ValueError):
    """Raised when a module declares an unsafe recovery identity."""


@dataclass(frozen=True, slots=True)
class StorageRecoveryContribution:
    """Bounded storage identities and limits supplied to the coordinator.

    The contribution deliberately contains no live storage path, database
    handle, repository, or restore ordering. Platform supplies those concerns
    while the application is quiesced.
    """

    id: str
    manifest_key: str
    archive_file: str
    archive_root: str
    introduced_in_format: int
    max_members: int
    max_bytes: int

    def __post_init__(self) -> None:
        if not _CONTRIBUTION_ID.fullmatch(self.id):
            raise RecoveryContributionError("recovery contribution id is invalid")
        if not _MANIFEST_KEY.fullmatch(self.manifest_key):
            raise RecoveryContributionError("recovery manifest key is invalid")
        archive_path = PurePosixPath(self.archive_file)
        if (
            archive_path.is_absolute()
            or len(archive_path.parts) != 1
            or archive_path.name in {"", ".", ".."}
        ):
            raise RecoveryContributionError("recovery archive file is unsafe")
        archive_root = PurePosixPath(self.archive_root)
        if (
            archive_root.is_absolute()
            or len(archive_root.parts) != 1
            or archive_root.name in {"", ".", ".."}
        ):
            raise RecoveryContributionError("recovery archive root is unsafe")
        if (
            isinstance(self.introduced_in_format, bool)
            or not isinstance(self.introduced_in_format, int)
            or self.introduced_in_format < 1
        ):
            raise RecoveryContributionError("recovery format version is invalid")
        for name, value in (
            ("member limit", self.max_members),
            ("byte limit", self.max_bytes),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise RecoveryContributionError(f"recovery {name} is invalid")
