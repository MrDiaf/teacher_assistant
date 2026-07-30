"""Create the manual course foundation.

Revision ID: 20260730_0010
Revises: 20260720_0009
Create Date: 2026-07-30
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260730_0010"
down_revision: str | None = "20260720_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "courses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("course_code", sa.String(length=64), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("term", sa.String(length=120), nullable=True),
        sa.Column("color", sa.String(length=7), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "active",
                "archived",
                name="course_status",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column(
            "source_type",
            sa.Enum(
                "manual",
                name="course_source_type",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
        ),
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
        sa.CheckConstraint("btrim(name) <> ''", name="ck_courses_name_not_blank"),
        sa.CheckConstraint(
            "course_code IS NULL OR btrim(course_code) <> ''",
            name="ck_courses_code_not_blank",
        ),
        sa.CheckConstraint(
            "term IS NULL OR btrim(term) <> ''",
            name="ck_courses_term_not_blank",
        ),
        sa.CheckConstraint(
            "color ~ '^#[0-9A-Fa-f]{6}$'",
            name="ck_courses_color_hex",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_courses_status", "courses", ["status"])


def downgrade() -> None:
    op.drop_index("ix_courses_status", table_name="courses")
    op.drop_table("courses")
