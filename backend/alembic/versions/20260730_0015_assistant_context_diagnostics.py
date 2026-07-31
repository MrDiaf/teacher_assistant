"""Add course-aware Assistant context and sanitized diagnostics.

Revision ID: 20260730_0015
Revises: 20260730_0014
Create Date: 2026-07-30
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260730_0015"
down_revision: str | None = "20260730_0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "assistant_messages",
        sa.Column(
            "citations",
            sa.JSON(),
            server_default=sa.text("'[]'::json"),
            nullable=False,
        ),
    )
    op.alter_column("assistant_messages", "citations", server_default=None)

    op.create_table(
        "assistant_context_audits",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("course_ids", sa.JSON(), nullable=False),
        sa.Column("note_ids", sa.JSON(), nullable=False),
        sa.Column("source_ids", sa.JSON(), nullable=False),
        sa.Column("slide_numbers", sa.JSON(), nullable=False),
        sa.Column("requires_clarification", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["assistant_jobs.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "job_id",
            name="uq_assistant_context_audits_job_id",
        ),
    )
    op.create_index(
        "ix_assistant_context_audits_job_id",
        "assistant_context_audits",
        ["job_id"],
        unique=False,
    )

    op.create_table(
        "diagnostic_errors",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("operation", sa.String(length=240), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("exception_type", sa.String(length=120), nullable=True),
        sa.Column("explanation", sa.JSON(), nullable=True),
        sa.Column("explanation_model", sa.String(length=100), nullable=True),
        sa.Column("explained_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_diagnostic_errors_code",
        "diagnostic_errors",
        ["code"],
    )
    op.create_index(
        "ix_diagnostic_errors_request_id",
        "diagnostic_errors",
        ["request_id"],
    )

    op.create_table(
        "diagnostic_audit_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("error_id", sa.Uuid(), nullable=False),
        sa.Column("action", sa.String(length=60), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["error_id"],
            ["diagnostic_errors.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_diagnostic_audit_records_error_id",
        "diagnostic_audit_records",
        ["error_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_diagnostic_audit_records_error_id",
        table_name="diagnostic_audit_records",
    )
    op.drop_table("diagnostic_audit_records")
    op.drop_index(
        "ix_diagnostic_errors_request_id",
        table_name="diagnostic_errors",
    )
    op.drop_index(
        "ix_diagnostic_errors_code",
        table_name="diagnostic_errors",
    )
    op.drop_table("diagnostic_errors")
    op.drop_index(
        "ix_assistant_context_audits_job_id",
        table_name="assistant_context_audits",
    )
    op.drop_table("assistant_context_audits")
    op.drop_column("assistant_messages", "citations")
