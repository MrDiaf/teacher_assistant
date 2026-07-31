"""Add actionable diagnostics to failed Assistant jobs.

Revision ID: 20260731_0016
Revises: 20260730_0015
Create Date: 2026-07-31
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260731_0016"
down_revision: str | None = "20260730_0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "assistant_jobs",
        sa.Column(
            "safe_error_details",
            sa.JSON(),
            server_default=sa.text("'{}'::json"),
            nullable=False,
        ),
    )
    op.alter_column("assistant_jobs", "safe_error_details", server_default=None)
    op.add_column(
        "assistant_jobs",
        sa.Column("diagnostic_error_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_assistant_jobs_diagnostic_error_id",
        "assistant_jobs",
        "diagnostic_errors",
        ["diagnostic_error_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_assistant_jobs_diagnostic_error_id",
        "assistant_jobs",
        ["diagnostic_error_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_assistant_jobs_diagnostic_error_id",
        table_name="assistant_jobs",
    )
    op.drop_constraint(
        "fk_assistant_jobs_diagnostic_error_id",
        "assistant_jobs",
        type_="foreignkey",
    )
    op.drop_column("assistant_jobs", "diagnostic_error_id")
    op.drop_column("assistant_jobs", "safe_error_details")
