"""Store safe assistant job error codes for correction feedback.

Revision ID: 20260720_0008
Revises: 20260719_0007
Create Date: 2026-07-20
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260720_0008"
down_revision: str | None = "20260719_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "assistant_jobs",
        sa.Column("safe_error_code", sa.String(length=80), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("assistant_jobs", "safe_error_code")
