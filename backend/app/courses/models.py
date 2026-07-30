import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Enum, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.calendar.models import enum_values
from app.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.course_sources.models import CourseSource


class CourseStatus(str, enum.Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class CourseSourceType(str, enum.Enum):
    MANUAL = "manual"


class Course(TimestampMixin, Base):
    __tablename__ = "courses"
    __table_args__ = (
        CheckConstraint("btrim(name) <> ''", name="ck_courses_name_not_blank"),
        CheckConstraint(
            "course_code IS NULL OR btrim(course_code) <> ''",
            name="ck_courses_code_not_blank",
        ),
        CheckConstraint(
            "term IS NULL OR btrim(term) <> ''",
            name="ck_courses_term_not_blank",
        ),
        CheckConstraint(
            "color ~ '^#[0-9A-Fa-f]{6}$'",
            name="ck_courses_color_hex",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    course_code: Mapped[str | None] = mapped_column(String(64))
    description: Mapped[str | None] = mapped_column(Text)
    term: Mapped[str | None] = mapped_column(String(120))
    color: Mapped[str] = mapped_column(String(7), nullable=False, default="#29584c")
    status: Mapped[CourseStatus] = mapped_column(
        Enum(
            CourseStatus,
            values_callable=enum_values,
            native_enum=False,
            create_constraint=True,
            length=32,
            name="course_status",
        ),
        nullable=False,
        default=CourseStatus.ACTIVE,
        index=True,
    )
    source_type: Mapped[CourseSourceType] = mapped_column(
        Enum(
            CourseSourceType,
            values_callable=enum_values,
            native_enum=False,
            create_constraint=True,
            length=32,
            name="course_source_type",
        ),
        nullable=False,
        default=CourseSourceType.MANUAL,
    )
    sources: Mapped[list["CourseSource"]] = relationship(
        back_populates="course",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )

    @property
    def source_count(self) -> int:
        return len(self.sources)
