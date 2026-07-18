"""Add recurrence exception identity.

Revision ID: 20260719_0002
Revises: 20260718_0001
Create Date: 2026-07-19
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260719_0002"
down_revision: str | None = "20260718_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "events",
        sa.Column("recurrence_original_start_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_events_recurrence_original_start_at",
        "events",
        ["recurrence_original_start_at"],
    )
    op.create_check_constraint(
        "ck_events_recurrence_exception_parent",
        "events",
        "recurrence_original_start_at IS NULL OR recurrence_parent_id IS NOT NULL",
    )
    op.create_unique_constraint(
        "uq_events_recurrence_exception",
        "events",
        ["recurrence_parent_id", "recurrence_original_start_at"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_events_recurrence_exception", "events", type_="unique")
    op.drop_constraint(
        "ck_events_recurrence_exception_parent", "events", type_="check"
    )
    op.drop_index("ix_events_recurrence_original_start_at", table_name="events")
    op.drop_column("events", "recurrence_original_start_at")
