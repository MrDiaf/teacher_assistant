"""Link courses to existing calendars.

Revision ID: 20260730_0014
Revises: 20260730_0013
Create Date: 2026-07-30
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260730_0014"
down_revision: str | None = "20260730_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "course_calendar_links",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("calendar_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["calendar_id"],
            ["calendars.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["course_id"],
            ["courses.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "course_id",
            "calendar_id",
            name="uq_course_calendar_links_course_calendar",
        ),
    )
    op.create_index(
        "ix_course_calendar_links_calendar_id",
        "course_calendar_links",
        ["calendar_id"],
    )
    op.create_index(
        "ix_course_calendar_links_course_id",
        "course_calendar_links",
        ["course_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_course_calendar_links_course_id",
        table_name="course_calendar_links",
    )
    op.drop_index(
        "ix_course_calendar_links_calendar_id",
        table_name="course_calendar_links",
    )
    op.drop_table("course_calendar_links")
