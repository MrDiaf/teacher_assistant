"""Add durable private document project metadata and tags.

Revision ID: 20260908_0021
Revises: 20260903_0020
Create Date: 2026-09-08
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260908_0021"
down_revision: str | None = "20260903_0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def timestamps() -> tuple[sa.Column, sa.Column]:
    return (
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )


def upgrade() -> None:
    op.create_table(
        "document_projects",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        *timestamps(),
        sa.CheckConstraint("btrim(title) <> ''", name="ck_document_projects_title_not_blank"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "document_tags",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("name_normalized", sa.String(128), nullable=False),
        sa.Column("color", sa.String(7), nullable=False),
        *timestamps(),
        sa.CheckConstraint("btrim(name) <> ''", name="ck_document_tags_name_not_blank"),
        sa.CheckConstraint("color ~ '^#[0-9A-Fa-f]{6}$'", name="ck_document_tags_color_hex"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name_normalized"),
    )
    op.create_table(
        "document_project_tags",
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("tag_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["document_projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tag_id"], ["document_tags.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("project_id", "tag_id"),
    )
    op.create_index("ix_document_project_tags_tag_id", "document_project_tags", ["tag_id"])


def downgrade() -> None:
    op.drop_index("ix_document_project_tags_tag_id", table_name="document_project_tags")
    op.drop_table("document_project_tags")
    op.drop_table("document_tags")
    op.drop_table("document_projects")
