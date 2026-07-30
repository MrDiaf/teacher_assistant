import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.course_sources.models import CourseSource
    from app.courses.models import Course


class Note(TimestampMixin, Base):
    __tablename__ = "notes"
    __table_args__ = (
        CheckConstraint("btrim(title) <> ''", name="ck_notes_title_not_blank"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    course_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False, default="")

    course: Mapped["Course"] = relationship()
    slide_references: Mapped[list["NoteSourceLink"]] = relationship(
        back_populates="note",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
        order_by="NoteSourceLink.created_at",
    )


class NoteSourceLink(TimestampMixin, Base):
    __tablename__ = "note_source_links"
    __table_args__ = (
        CheckConstraint(
            """
            (start_slide IS NULL AND end_slide IS NULL)
            OR
            (
                start_slide IS NOT NULL
                AND end_slide IS NOT NULL
                AND start_slide >= 1
                AND end_slide >= start_slide
            )
            """,
            name="ck_note_source_links_slide_range",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    note_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("notes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("course_sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    start_slide: Mapped[int | None] = mapped_column(Integer)
    end_slide: Mapped[int | None] = mapped_column(Integer)
    label: Mapped[str | None] = mapped_column(String(240))

    note: Mapped[Note] = relationship(back_populates="slide_references")
    source: Mapped["CourseSource"] = relationship(lazy="joined")
