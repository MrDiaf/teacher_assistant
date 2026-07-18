"""Require imported calendars to finalize before commit.

Revision ID: 20260719_0004
Revises: 20260719_0003
Create Date: 2026-07-19
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260719_0004"
down_revision: str | None = "20260719_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE FUNCTION ensure_calendar_import_finalized()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        DECLARE
            still_importing boolean;
        BEGIN
            SELECT is_importing INTO still_importing
            FROM calendars
            WHERE id = NEW.id;

            IF still_importing THEN
                RAISE EXCEPTION USING
                    ERRCODE = '23514',
                    MESSAGE = 'calendar_import_not_finalized';
            END IF;
            RETURN NULL;
        END;
        $$;
        """
    )
    op.execute(
        """
        CREATE CONSTRAINT TRIGGER calendars_require_finalized_import
        AFTER INSERT OR UPDATE OF is_importing ON calendars
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW EXECUTE FUNCTION ensure_calendar_import_finalized()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS calendars_require_finalized_import ON calendars")
    op.execute("DROP FUNCTION IF EXISTS ensure_calendar_import_finalized")
