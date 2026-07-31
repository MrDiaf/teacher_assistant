"""Allow owner-cancelled Assistant jobs.

Revision ID: 20260731_0017
Revises: 20260731_0016
Create Date: 2026-07-31
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260731_0017"
down_revision: str | None = "20260731_0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("assistant_job_status", "assistant_jobs", type_="check")
    op.create_check_constraint(
        "assistant_job_status",
        "assistant_jobs",
        "status IN ('queued', 'preparing_context', 'running', 'validating', "
        "'awaiting_confirmation', 'completed', 'failed', 'cancelled')",
    )


def downgrade() -> None:
    op.execute(
        "UPDATE assistant_jobs SET status = 'failed', "
        "safe_error = 'The Assistant request was cancelled.' "
        "WHERE status = 'cancelled'"
    )
    op.drop_constraint("assistant_job_status", "assistant_jobs", type_="check")
    op.create_check_constraint(
        "assistant_job_status",
        "assistant_jobs",
        "status IN ('queued', 'preparing_context', 'running', 'validating', "
        "'awaiting_confirmation', 'completed', 'failed')",
    )
