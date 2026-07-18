"""Add private ICS subscriptions and protected refresh state.

Revision ID: 20260719_0005
Revises: 20260719_0004
Create Date: 2026-07-19
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260719_0005"
down_revision: str | None = "20260719_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("calendars", sa.Column("subscription_url", sa.Text(), nullable=True))
    op.add_column(
        "calendars",
        sa.Column("subscription_last_synced_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "calendars",
        sa.Column("subscription_next_sync_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("calendars", sa.Column("subscription_error", sa.Text(), nullable=True))
    op.create_index(
        "ix_calendars_subscription_next_sync_at",
        "calendars",
        ["subscription_next_sync_at"],
    )
    op.create_check_constraint(
        "ck_calendars_subscription_source",
        "calendars",
        "subscription_url IS NULL OR (source_type = 'ics_import' AND is_read_only)",
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
                    IF NEW.is_importing OR NEW.subscription_url IS NOT NULL THEN
                        RAISE EXCEPTION USING ERRCODE = '42501', MESSAGE = 'calendar_import_state';
                    END IF;
                ELSIF NEW.is_importing THEN
                    IF NEW.is_read_only THEN
                        RAISE EXCEPTION USING ERRCODE = '42501', MESSAGE = 'calendar_import_state';
                    END IF;
                ELSIF NOT NEW.is_read_only THEN
                    RAISE EXCEPTION USING ERRCODE = '42501', MESSAGE = 'calendar_source_protected';
                END IF;
                RETURN NEW;
            END IF;

            IF TG_OP = 'DELETE' THEN
                IF OLD.is_read_only THEN
                    RAISE EXCEPTION USING ERRCODE = '42501', MESSAGE = 'calendar_read_only';
                END IF;
                IF OLD.source_type <> 'local' THEN
                    RAISE EXCEPTION USING ERRCODE = '42501', MESSAGE = 'calendar_source_protected';
                END IF;
                RETURN OLD;
            END IF;

            IF NEW.source_type IS DISTINCT FROM OLD.source_type THEN
                RAISE EXCEPTION USING ERRCODE = '42501', MESSAGE = 'calendar_source_protected';
            END IF;

            IF OLD.is_importing THEN
                IF OLD.source_type <> 'ics_import' OR NEW.is_importing OR NOT NEW.is_read_only THEN
                    RAISE EXCEPTION USING ERRCODE = '42501', MESSAGE = 'calendar_import_state';
                END IF;
                RETURN NEW;
            END IF;

            IF NEW.is_importing IS DISTINCT FROM OLD.is_importing THEN
                IF OLD.source_type <> 'ics_import' OR NOT OLD.is_read_only OR
                   NOT NEW.is_read_only OR OLD.subscription_url IS NULL THEN
                    RAISE EXCEPTION USING ERRCODE = '42501', MESSAGE = 'calendar_import_state';
                END IF;
                RETURN NEW;
            END IF;

            IF OLD.is_read_only AND (
                NEW.name IS DISTINCT FROM OLD.name OR
                NEW.description IS DISTINCT FROM OLD.description OR
                NEW.color IS DISTINCT FROM OLD.color OR
                NEW.subscription_url IS DISTINCT FROM OLD.subscription_url
            ) THEN
                RAISE EXCEPTION USING ERRCODE = '42501', MESSAGE = 'calendar_read_only';
            END IF;
            IF NOT NEW.is_read_only AND NEW.source_type <> 'local' THEN
                RAISE EXCEPTION USING ERRCODE = '42501', MESSAGE = 'calendar_source_protected';
            END IF;
            RETURN NEW;
        END;
        $$;
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION enforce_writable_calendar_event()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        DECLARE
            protected boolean;
            syncing boolean;
        BEGIN
            IF TG_OP = 'DELETE' THEN
                SELECT is_read_only, is_importing INTO protected, syncing
                FROM calendars WHERE id = OLD.calendar_id;
                IF protected AND NOT syncing THEN
                    RAISE EXCEPTION USING ERRCODE = '42501', MESSAGE = 'calendar_read_only';
                END IF;
                RETURN OLD;
            END IF;

            IF TG_OP = 'UPDATE' THEN
                SELECT is_read_only, is_importing INTO protected, syncing
                FROM calendars WHERE id = OLD.calendar_id;
                IF protected AND NOT syncing THEN
                    RAISE EXCEPTION USING ERRCODE = '42501', MESSAGE = 'calendar_read_only';
                END IF;
            END IF;

            SELECT is_read_only, is_importing INTO protected, syncing
            FROM calendars WHERE id = NEW.calendar_id;
            IF protected AND NOT syncing THEN
                RAISE EXCEPTION USING ERRCODE = '42501', MESSAGE = 'calendar_read_only';
            END IF;
            RETURN NEW;
        END;
        $$;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION enforce_writable_calendar_event()
        RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE protected boolean;
        BEGIN
            IF TG_OP = 'DELETE' THEN
                SELECT is_read_only INTO protected FROM calendars WHERE id = OLD.calendar_id;
                IF protected THEN
                    RAISE EXCEPTION USING ERRCODE = '42501', MESSAGE = 'calendar_read_only';
                END IF;
                RETURN OLD;
            END IF;
            IF TG_OP = 'UPDATE' THEN
                SELECT is_read_only INTO protected FROM calendars WHERE id = OLD.calendar_id;
                IF protected THEN
                    RAISE EXCEPTION USING ERRCODE = '42501', MESSAGE = 'calendar_read_only';
                END IF;
            END IF;
            SELECT is_read_only INTO protected FROM calendars WHERE id = NEW.calendar_id;
            IF protected THEN
                RAISE EXCEPTION USING ERRCODE = '42501', MESSAGE = 'calendar_read_only';
            END IF;
            RETURN NEW;
        END; $$;
        """
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
                            ERRCODE = '42501', MESSAGE = 'calendar_import_state';
                    END IF;
                ELSIF NEW.is_importing THEN
                    IF NEW.is_read_only THEN
                        RAISE EXCEPTION USING
                            ERRCODE = '42501', MESSAGE = 'calendar_import_state';
                    END IF;
                ELSIF NOT NEW.is_read_only THEN
                    RAISE EXCEPTION USING
                        ERRCODE = '42501', MESSAGE = 'calendar_source_protected';
                END IF;
                RETURN NEW;
            END IF;

            IF TG_OP = 'DELETE' THEN
                IF OLD.is_read_only THEN
                    RAISE EXCEPTION USING ERRCODE = '42501', MESSAGE = 'calendar_read_only';
                END IF;
                IF OLD.source_type <> 'local' THEN
                    RAISE EXCEPTION USING
                        ERRCODE = '42501', MESSAGE = 'calendar_source_protected';
                END IF;
                RETURN OLD;
            END IF;

            IF NEW.source_type IS DISTINCT FROM OLD.source_type THEN
                RAISE EXCEPTION USING
                    ERRCODE = '42501', MESSAGE = 'calendar_source_protected';
            END IF;
            IF OLD.is_importing THEN
                IF OLD.source_type <> 'ics_import' OR NEW.is_importing OR NOT NEW.is_read_only THEN
                    RAISE EXCEPTION USING
                        ERRCODE = '42501', MESSAGE = 'calendar_import_state';
                END IF;
                RETURN NEW;
            END IF;
            IF NEW.is_importing IS DISTINCT FROM OLD.is_importing THEN
                RAISE EXCEPTION USING
                    ERRCODE = '42501', MESSAGE = 'calendar_import_state';
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
                    ERRCODE = '42501', MESSAGE = 'calendar_source_protected';
            END IF;
            RETURN NEW;
        END;
        $$;
        """
    )
    op.drop_constraint("ck_calendars_subscription_source", "calendars", type_="check")
    op.drop_index("ix_calendars_subscription_next_sync_at", table_name="calendars")
    op.drop_column("calendars", "subscription_error")
    op.drop_column("calendars", "subscription_next_sync_at")
    op.drop_column("calendars", "subscription_last_synced_at")
    op.drop_column("calendars", "subscription_url")
