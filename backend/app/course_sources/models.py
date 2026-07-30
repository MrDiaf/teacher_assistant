import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.calendar.models import enum_values
from app.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.courses.models import Course


class CourseSourceType(str, enum.Enum):
    LITERATURE = "literature"
    SLIDES = "slides"


class ExtractionStatus(str, enum.Enum):
    NOT_STARTED = "not_started"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    UNSUPPORTED = "unsupported"


class CourseSource(TimestampMixin, Base):
    __tablename__ = "course_sources"
    __table_args__ = (
        CheckConstraint("btrim(display_name) <> ''", name="ck_course_sources_display_name"),
        CheckConstraint("btrim(original_filename) <> ''", name="ck_course_sources_filename"),
        CheckConstraint("file_size > 0", name="ck_course_sources_file_size"),
        CheckConstraint(
            "content_hash ~ '^[0-9a-f]{64}$'",
            name="ck_course_sources_content_hash",
        ),
        UniqueConstraint("storage_path", name="uq_course_sources_storage_path"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    course_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_type: Mapped[CourseSourceType] = mapped_column(
        Enum(
            CourseSourceType,
            values_callable=enum_values,
            native_enum=False,
            create_constraint=True,
            length=32,
            name="course_material_type",
        ),
        nullable=False,
        index=True,
    )
    display_name: Mapped[str] = mapped_column(String(240), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(64), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(160), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(500))
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    extraction_status: Mapped[ExtractionStatus] = mapped_column(
        Enum(
            ExtractionStatus,
            values_callable=enum_values,
            native_enum=False,
            create_constraint=True,
            length=32,
            name="course_source_extraction_status",
        ),
        nullable=False,
        default=ExtractionStatus.NOT_STARTED,
        index=True,
    )
    extraction_error: Mapped[str | None] = mapped_column(Text)

    course: Mapped["Course"] = relationship(back_populates="sources")
    extracted_contents: Mapped[list["ExtractedSourceText"]] = relationship(
        back_populates="source",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )

    @property
    def extracted_text_count(self) -> int:
        return len(self.extracted_contents)


class ExtractedSourceText(TimestampMixin, Base):
    __tablename__ = "course_source_text"
    __table_args__ = (
        CheckConstraint(
            "page_or_slide_number >= 1",
            name="ck_course_source_text_page_number",
        ),
        CheckConstraint("btrim(text) <> ''", name="ck_course_source_text_not_blank"),
        CheckConstraint(
            "content_hash ~ '^[0-9a-f]{64}$'",
            name="ck_course_source_text_content_hash",
        ),
        UniqueConstraint(
            "source_id",
            "page_or_slide_number",
            name="uq_course_source_text_page",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    source_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("course_sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    page_or_slide_number: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    source: Mapped[CourseSource] = relationship(back_populates="extracted_contents")
