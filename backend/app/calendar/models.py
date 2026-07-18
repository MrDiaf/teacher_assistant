import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Enum, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin


class CalendarSourceType(str, enum.Enum):
    LOCAL = "local"
    ICS_IMPORT = "ics_import"


class EventStatus(str, enum.Enum):
    CONFIRMED = "confirmed"
    TENTATIVE = "tentative"
    CANCELLED = "cancelled"


def enum_values(enum_type: type[enum.Enum]) -> list[str]:
    return [member.value for member in enum_type]


class Calendar(TimestampMixin, Base):
    __tablename__ = "calendars"
    __table_args__ = (CheckConstraint("char_length(color) = 7", name="ck_calendars_color_length"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    color: Mapped[str] = mapped_column(String(7), nullable=False, default="#29584c")
    is_visible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_read_only: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    source_type: Mapped[CalendarSourceType] = mapped_column(
        Enum(
            CalendarSourceType,
            values_callable=enum_values,
            native_enum=False,
            create_constraint=True,
            length=32,
            name="calendar_source_type",
        ),
        nullable=False,
        default=CalendarSourceType.LOCAL,
    )

    events: Mapped[list["CalendarEvent"]] = relationship(
        back_populates="calendar", cascade="all, delete-orphan", passive_deletes=True
    )


class CalendarEvent(TimestampMixin, Base):
    __tablename__ = "events"
    __table_args__ = (CheckConstraint("end_at > start_at", name="ck_events_valid_time_range"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    calendar_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("calendars.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(String(500))
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    all_day: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="Europe/Stockholm")
    recurrence_rule: Mapped[str | None] = mapped_column(Text)
    recurrence_parent_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("events.id", ondelete="SET NULL"), index=True
    )
    status: Mapped[EventStatus] = mapped_column(
        Enum(
            EventStatus,
            values_callable=enum_values,
            native_enum=False,
            create_constraint=True,
            length=32,
            name="event_status",
        ),
        nullable=False,
        default=EventStatus.CONFIRMED,
    )

    calendar: Mapped[Calendar] = relationship(back_populates="events")
