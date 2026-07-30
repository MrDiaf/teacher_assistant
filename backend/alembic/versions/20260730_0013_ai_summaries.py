"""Add AI model persistence and provenance-aware note summaries.

Revision ID: 20260730_0013
Revises: 20260730_0012
Create Date: 2026-07-30
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260730_0013"
down_revision: str | None = "20260730_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "assistant_jobs",
        sa.Column(
            "model",
            sa.String(length=100),
            server_default="gpt-5.6-sol",
            nullable=False,
        ),
    )

    op.create_table(
        "note_summaries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("note_id", sa.Uuid(), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "queued",
                "running",
                "validating",
                "completed",
                "failed",
                name="note_summary_status",
                native_enum=False,
                create_constraint=True,
                length=20,
            ),
            nullable=False,
        ),
        sa.Column("summary_json", sa.JSON(), nullable=True),
        sa.Column("note_content_hash", sa.String(length=64), nullable=False),
        sa.Column("slide_content_hash", sa.String(length=64), nullable=False),
        sa.Column("safe_error", sa.Text(), nullable=True),
        sa.Column("safe_error_code", sa.String(length=80), nullable=True),
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
        sa.CheckConstraint(
            "btrim(model) <> ''",
            name="ck_note_summaries_model",
        ),
        sa.CheckConstraint(
            "note_content_hash ~ '^[0-9a-f]{64}$'",
            name="ck_note_summaries_note_hash",
        ),
        sa.CheckConstraint(
            "slide_content_hash ~ '^[0-9a-f]{64}$'",
            name="ck_note_summaries_slide_hash",
        ),
        sa.ForeignKeyConstraint(["note_id"], ["notes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_note_summaries_note_id",
        "note_summaries",
        ["note_id"],
    )
    op.create_index(
        "ix_note_summaries_status",
        "note_summaries",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index("ix_note_summaries_status", table_name="note_summaries")
    op.drop_index("ix_note_summaries_note_id", table_name="note_summaries")
    op.drop_table("note_summaries")
    op.drop_column("assistant_jobs", "model")
