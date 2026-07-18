"""Create calendar and event tables with read-only guards.

Revision ID: 20260718_0001
Revises:
Create Date: 2026-07-18
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260718_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "calendars",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("color", sa.String(length=7), nullable=False),
        sa.Column("is_visible", sa.Boolean(), nullable=False),
        sa.Column("is_read_only", sa.Boolean(), nullable=False),
        sa.Column(
            "source_type",
            sa.Enum(
                "local",
                "ics_import",
                name="calendar_source_type",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("char_length(color) = 7", name="ck_calendars_color_length"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("calendar_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("location", sa.String(length=500), nullable=True),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("all_day", sa.Boolean(), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("recurrence_rule", sa.Text(), nullable=True),
        sa.Column("recurrence_parent_id", sa.Uuid(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "confirmed",
                "tentative",
                "cancelled",
                name="event_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("end_at > start_at", name="ck_events_valid_time_range"),
        sa.ForeignKeyConstraint(["calendar_id"], ["calendars.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recurrence_parent_id"], ["events.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_events_calendar_id", "events", ["calendar_id"])
    op.create_index("ix_events_end_at", "events", ["end_at"])
    op.create_index("ix_events_recurrence_parent_id", "events", ["recurrence_parent_id"])
    op.create_index("ix_events_start_at", "events", ["start_at"])

    op.execute(
        """
        CREATE FUNCTION enforce_calendar_protection()
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
    op.execute(
        """
        CREATE TRIGGER calendars_enforce_protection
        BEFORE INSERT OR UPDATE OR DELETE ON calendars
        FOR EACH ROW EXECUTE FUNCTION enforce_calendar_protection()
        """
    )
    op.execute(
        """
        CREATE FUNCTION enforce_writable_calendar_event()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        DECLARE
            protected boolean;
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
        END;
        $$;

        """
    )
    op.execute(
        """
        CREATE TRIGGER events_enforce_writable_calendar
        BEFORE INSERT OR UPDATE OR DELETE ON events
        FOR EACH ROW EXECUTE FUNCTION enforce_writable_calendar_event()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS events_enforce_writable_calendar ON events")
    op.execute("DROP FUNCTION IF EXISTS enforce_writable_calendar_event")
    op.execute("DROP TRIGGER IF EXISTS calendars_enforce_protection ON calendars")
    op.execute("DROP FUNCTION IF EXISTS enforce_calendar_protection")
    op.drop_index("ix_events_start_at", table_name="events")
    op.drop_index("ix_events_recurrence_parent_id", table_name="events")
    op.drop_index("ix_events_end_at", table_name="events")
    op.drop_index("ix_events_calendar_id", table_name="events")
    op.drop_table("events")
    op.drop_table("calendars")
