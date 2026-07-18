"""Add ICS import state and external event UID.

Revision ID: 20260719_0003
Revises: 20260719_0002
Create Date: 2026-07-19
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260719_0003"
down_revision: str | None = "20260719_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "calendars",
        sa.Column(
            "is_importing",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
    )
    op.add_column("events", sa.Column("external_uid", sa.String(length=500), nullable=True))
    op.create_unique_constraint(
        "uq_events_calendar_external_uid",
        "events",
        ["calendar_id", "external_uid"],
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION enforce_calendar_protection()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF TG_OP = 'INSERT' THEN
                IF NEW.source_type = 'local' THEN
                    IF NEW.is_importing THEN
                        RAISE EXCEPTION USING
                            ERRCODE = '42501',
                            MESSAGE = 'calendar_import_state';
                    END IF;
                ELSIF NEW.is_importing THEN
                    IF NEW.is_read_only THEN
                        RAISE EXCEPTION USING
                            ERRCODE = '42501',
                            MESSAGE = 'calendar_import_state';
                    END IF;
                ELSIF NOT NEW.is_read_only THEN
                    RAISE EXCEPTION USING
                        ERRCODE = '42501',
                        MESSAGE = 'calendar_source_protected';
                END IF;
                RETURN NEW;
            END IF;

            IF TG_OP = 'DELETE' THEN
                IF OLD.is_read_only THEN
                    RAISE EXCEPTION USING ERRCODE = '42501', MESSAGE = 'calendar_read_only';
                END IF;
                IF OLD.source_type <> 'local' THEN
                    RAISE EXCEPTION USING
                        ERRCODE = '42501',
                        MESSAGE = 'calendar_source_protected';
                END IF;
                RETURN OLD;
            END IF;

            IF NEW.source_type IS DISTINCT FROM OLD.source_type THEN
                RAISE EXCEPTION USING
                    ERRCODE = '42501',
                    MESSAGE = 'calendar_source_protected';
            END IF;

            IF OLD.is_importing THEN
                IF OLD.source_type <> 'ics_import' OR NEW.is_importing OR NOT NEW.is_read_only THEN
                    RAISE EXCEPTION USING
                        ERRCODE = '42501',
                        MESSAGE = 'calendar_import_state';
                END IF;
                RETURN NEW;
            END IF;

            IF NEW.is_importing IS DISTINCT FROM OLD.is_importing THEN
                RAISE EXCEPTION USING
                    ERRCODE = '42501',
                    MESSAGE = 'calendar_import_state';
            END IF;
            IF OLD.is_read_only AND (
                NEW.name IS DISTINCT FROM OLD.name OR
                NEW.description IS DISTINCT FROM OLD.description OR
                NEW.color IS DISTINCT FROM OLD.color
            ) THEN
                RAISE EXCEPTION USING ERRCODE = '42501', MESSAGE = 'calendar_read_only';
            END IF;
            IF NOT NEW.is_read_only AND NEW.source_type <> 'local' THEN
                RAISE EXCEPTION USING
                    ERRCODE = '42501',
                    MESSAGE = 'calendar_source_protected';
            END IF;
            RETURN NEW;
        END;
        $$;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION enforce_calendar_protection()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF TG_OP = 'INSERT' THEN
                IF NEW.source_type <> 'local' AND NOT NEW.is_read_only THEN
                    RAISE EXCEPTION USING
                        ERRCODE = '42501',
                        MESSAGE = 'calendar_source_protected';
                END IF;
                RETURN NEW;
            END IF;

            IF TG_OP = 'DELETE' THEN
                IF OLD.is_read_only THEN
                    RAISE EXCEPTION USING ERRCODE = '42501', MESSAGE = 'calendar_read_only';
                END IF;
                IF OLD.source_type <> 'local' THEN
                    RAISE EXCEPTION USING
                        ERRCODE = '42501',
                        MESSAGE = 'calendar_source_protected';
                END IF;
                RETURN OLD;
            END IF;

            IF NEW.source_type IS DISTINCT FROM OLD.source_type THEN
                RAISE EXCEPTION USING
                    ERRCODE = '42501',
                    MESSAGE = 'calendar_source_protected';
            END IF;
            IF OLD.is_read_only AND (
                NEW.name IS DISTINCT FROM OLD.name OR
                NEW.description IS DISTINCT FROM OLD.description OR
                NEW.color IS DISTINCT FROM OLD.color
            ) THEN
                RAISE EXCEPTION USING ERRCODE = '42501', MESSAGE = 'calendar_read_only';
            END IF;
            IF NOT NEW.is_read_only AND NEW.source_type <> 'local' THEN
                RAISE EXCEPTION USING
                    ERRCODE = '42501',
                    MESSAGE = 'calendar_source_protected';
            END IF;
            RETURN NEW;
        END;
        $$;
        """
    )
    op.drop_constraint("uq_events_calendar_external_uid", "events", type_="unique")
    op.drop_column("events", "external_uid")
    op.drop_column("calendars", "is_importing")
