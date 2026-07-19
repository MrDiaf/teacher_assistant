"""Add validated assistant calendar proposals.

Revision ID: 20260719_0007
Revises: 20260719_0006
Create Date: 2026-07-19
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260719_0007"
down_revision: str | None = "20260719_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("assistant_job_status", "assistant_jobs", type_="check")
    op.alter_column(
        "assistant_jobs",
        "status",
        existing_type=sa.String(length=17),
        type_=sa.String(length=32),
        existing_nullable=False,
    )
    op.create_check_constraint(
        "assistant_job_status",
        "assistant_jobs",
        "status IN ('queued', 'preparing_context', 'running', 'validating', "
        "'awaiting_confirmation', 'completed', 'failed')",
    )
    op.create_table(
        "assistant_proposals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "awaiting_confirmation",
                "confirmed",
                "rejected",
                "executing",
                "completed",
                "failed",
                "expired",
                name="assistant_proposal_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("summary", sa.String(length=240), nullable=False),
        sa.Column("actions", sa.JSON(), nullable=False),
        sa.Column("baselines", sa.JSON(), nullable=False),
        sa.Column("review_items", sa.JSON(), nullable=False),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.Column("affected_events", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("safe_error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"], ["assistant_conversations.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["job_id"], ["assistant_jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_id"),
    )
    op.create_index(
        "ix_assistant_proposals_conversation_id",
        "assistant_proposals",
        ["conversation_id"],
    )
    op.create_table(
        "assistant_proposal_actions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("proposal_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("operation", sa.String(length=40), nullable=False),
        sa.Column("target_calendar_id", sa.Uuid(), nullable=True),
        sa.Column("target_event_id", sa.Uuid(), nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("safe_error", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["proposal_id"], ["assistant_proposals.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "proposal_id", "position", name="uq_proposal_action_position"
        ),
    )
    op.create_index(
        "ix_assistant_proposal_actions_proposal_id",
        "assistant_proposal_actions",
        ["proposal_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_assistant_proposal_actions_proposal_id",
        table_name="assistant_proposal_actions",
    )
    op.drop_table("assistant_proposal_actions")
    op.drop_index(
        "ix_assistant_proposals_conversation_id", table_name="assistant_proposals"
    )
    op.drop_table("assistant_proposals")
    op.execute(
        "UPDATE assistant_jobs SET status = 'failed' "
        "WHERE status = 'awaiting_confirmation'"
    )
    op.drop_constraint("assistant_job_status", "assistant_jobs", type_="check")
    op.alter_column(
        "assistant_jobs",
        "status",
        existing_type=sa.String(length=32),
        type_=sa.String(length=17),
        existing_nullable=False,
    )
    op.create_check_constraint(
        "assistant_job_status",
        "assistant_jobs",
        "status IN ('queued', 'preparing_context', 'running', 'validating', "
        "'completed', 'failed')",
    )
