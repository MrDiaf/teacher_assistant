"""Add course notes and validated slide-reference links.

Revision ID: 20260730_0012
Revises: 20260730_0011
Create Date: 2026-07-30
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260730_0012"
down_revision: str | None = "20260730_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "notes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
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
            "btrim(title) <> ''",
            name="ck_notes_title_not_blank",
        ),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notes_course_id", "notes", ["course_id"])

    op.create_table(
        "note_source_links",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("note_id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("start_slide", sa.Integer(), nullable=True),
        sa.Column("end_slide", sa.Integer(), nullable=True),
        sa.Column("label", sa.String(length=240), nullable=True),
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
            """
            (start_slide IS NULL AND end_slide IS NULL)
            OR
            (
                start_slide IS NOT NULL
                AND end_slide IS NOT NULL
                AND start_slide >= 1
                AND end_slide >= start_slide
            )
            """,
            name="ck_note_source_links_slide_range",
        ),
        sa.ForeignKeyConstraint(["note_id"], ["notes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["course_sources.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_note_source_links_note_id",
        "note_source_links",
        ["note_id"],
    )
    op.create_index(
        "ix_note_source_links_source_id",
        "note_source_links",
        ["source_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_note_source_links_source_id",
        table_name="note_source_links",
    )
    op.drop_index(
        "ix_note_source_links_note_id",
        table_name="note_source_links",
    )
    op.drop_table("note_source_links")
    op.drop_index("ix_notes_course_id", table_name="notes")
    op.drop_table("notes")
