"""Add the owner password and per-address sign-in cooldowns.

Revision ID: 20261007_0022
Revises: 20260908_0021
Create Date: 2026-10-07
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261007_0022"
down_revision: str | None = "20260908_0021"
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
        "access_password",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("session_secret", sa.String(128), nullable=False),
        *timestamps(),
        sa.CheckConstraint("id = 1", name="ck_access_password_single_row"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "access_login_throttles",
        sa.Column("client_key", sa.String(64), nullable=False),
        sa.Column("failed_attempts", sa.Integer(), nullable=False),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        *timestamps(),
        sa.PrimaryKeyConstraint("client_key"),
    )


def downgrade() -> None:
    op.drop_table("access_login_throttles")
    op.drop_table("access_password")
