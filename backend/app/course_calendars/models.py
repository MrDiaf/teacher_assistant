import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.calendar.models import Calendar
    from app.courses.models import Course


class CourseCalendarLink(Base):
    __tablename__ = "course_calendar_links"
    __table_args__ = (
        UniqueConstraint(
            "course_id",
            "calendar_id",
            name="uq_course_calendar_links_course_calendar",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    course_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    calendar_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("calendars.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    course: Mapped["Course"] = relationship(back_populates="calendar_links")
    calendar: Mapped["Calendar"] = relationship(lazy="joined")
