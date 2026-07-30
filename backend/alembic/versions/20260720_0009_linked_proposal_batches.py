"""Allow one assistant job to own linked proposal batches.

Revision ID: 20260720_0009
Revises: 20260720_0008
Create Date: 2026-07-20
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260720_0009"
down_revision: str | None = "20260720_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "assistant_proposals_job_id_key", "assistant_proposals", type_="unique"
    )
    op.add_column(
        "assistant_proposals",
        sa.Column("batch_position", sa.Integer(), server_default="1", nullable=False),
    )
    op.add_column(
        "assistant_proposals",
        sa.Column("batch_count", sa.Integer(), server_default="1", nullable=False),
    )
    op.alter_column("assistant_proposals", "batch_position", server_default=None)
    op.alter_column("assistant_proposals", "batch_count", server_default=None)
    op.create_check_constraint(
        "assistant_proposal_batch_position",
        "assistant_proposals",
        "batch_position >= 1 AND batch_position <= batch_count",
    )
    op.create_check_constraint(
        "assistant_proposal_batch_count",
        "assistant_proposals",
        "batch_count >= 1 AND batch_count <= 10",
    )
    op.create_unique_constraint(
        "uq_assistant_proposal_job_batch",
        "assistant_proposals",
        ["job_id", "batch_position"],
    )
    op.create_index(
        "ix_assistant_proposals_job_id", "assistant_proposals", ["job_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_assistant_proposals_job_id", table_name="assistant_proposals")
    op.drop_constraint(
        "uq_assistant_proposal_job_batch", "assistant_proposals", type_="unique"
    )
    op.drop_constraint(
        "assistant_proposal_batch_count", "assistant_proposals", type_="check"
    )
    op.drop_constraint(
        "assistant_proposal_batch_position", "assistant_proposals", type_="check"
    )
    op.drop_column("assistant_proposals", "batch_count")
    op.drop_column("assistant_proposals", "batch_position")
    op.create_unique_constraint(
        "assistant_proposals_job_id_key", "assistant_proposals", ["job_id"]
    )
