"""Recognize the retired, unimplemented integration revision.

Revision ID: 20260903_0019
Revises: 20260831_0018
Create Date: 2026-09-03

Some development installations briefly ran an unshipped integration migration
before that roadmap was retired. Its unused tables are left intact so no local
data is destroyed implicitly. M20 uses separate mail-prefixed tables in the
following revision. Fresh installations safely run this no-op compatibility
marker before M20.
"""

from collections.abc import Sequence

revision: str = "20260903_0019"
down_revision: str | None = "20260831_0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
