"""Add separated course material storage metadata and extracted text.

Revision ID: 20260730_0011
Revises: 20260730_0010
Create Date: 2026-07-30
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260730_0011"
down_revision: str | None = "20260730_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "course_sources",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column(
            "source_type",
            sa.Enum(
                "literature",
                "slides",
                name="course_material_type",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("display_name", sa.String(length=240), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("stored_filename", sa.String(length=64), nullable=False),
        sa.Column("mime_type", sa.String(length=160), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("external_id", sa.String(length=500), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "extraction_status",
            sa.Enum(
                "not_started",
                "queued",
                "processing",
                "completed",
                "failed",
                "unsupported",
                name="course_source_extraction_status",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("extraction_error", sa.Text(), nullable=True),
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
            "btrim(display_name) <> ''",
            name="ck_course_sources_display_name",
        ),
        sa.CheckConstraint(
            "btrim(original_filename) <> ''",
            name="ck_course_sources_filename",
        ),
        sa.CheckConstraint("file_size > 0", name="ck_course_sources_file_size"),
        sa.CheckConstraint(
            "content_hash ~ '^[0-9a-f]{64}$'",
            name="ck_course_sources_content_hash",
        ),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_path", name="uq_course_sources_storage_path"),
    )
    op.create_index("ix_course_sources_course_id", "course_sources", ["course_id"])
    op.create_index(
        "ix_course_sources_extraction_status",
        "course_sources",
        ["extraction_status"],
    )
    op.create_index("ix_course_sources_source_type", "course_sources", ["source_type"])

    op.create_table(
        "course_source_text",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("page_or_slide_number", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
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
            "page_or_slide_number >= 1",
            name="ck_course_source_text_page_number",
        ),
        sa.CheckConstraint(
            "btrim(text) <> ''",
            name="ck_course_source_text_not_blank",
        ),
        sa.CheckConstraint(
            "content_hash ~ '^[0-9a-f]{64}$'",
            name="ck_course_source_text_content_hash",
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["course_sources.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_id",
            "page_or_slide_number",
            name="uq_course_source_text_page",
        ),
    )
    op.create_index(
        "ix_course_source_text_source_id",
        "course_source_text",
        ["source_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_course_source_text_source_id",
        table_name="course_source_text",
    )
    op.drop_table("course_source_text")
    op.drop_index("ix_course_sources_source_type", table_name="course_sources")
    op.drop_index(
        "ix_course_sources_extraction_status",
        table_name="course_sources",
    )
    op.drop_index("ix_course_sources_course_id", table_name="course_sources")
    op.drop_table("course_sources")
