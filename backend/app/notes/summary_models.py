import enum
import uuid

from sqlalchemy import JSON, CheckConstraint, Enum, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.calendar.models import enum_values
from app.database.base import Base, TimestampMixin


class NoteSummaryStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"


class NoteSummary(TimestampMixin, Base):
    __tablename__ = "note_summaries"
    __table_args__ = (
        CheckConstraint("btrim(model) <> ''", name="ck_note_summaries_model"),
        CheckConstraint(
            "note_content_hash ~ '^[0-9a-f]{64}$'",
            name="ck_note_summaries_note_hash",
        ),
        CheckConstraint(
            "slide_content_hash ~ '^[0-9a-f]{64}$'",
            name="ck_note_summaries_slide_hash",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    note_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("notes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[NoteSummaryStatus] = mapped_column(
        Enum(
            NoteSummaryStatus,
            values_callable=enum_values,
            native_enum=False,
            create_constraint=True,
            length=20,
            name="note_summary_status",
        ),
        nullable=False,
        default=NoteSummaryStatus.QUEUED,
        index=True,
    )
    summary_json: Mapped[dict | None] = mapped_column(JSON)
    note_content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    slide_content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    safe_error: Mapped[str | None] = mapped_column(Text)
    safe_error_code: Mapped[str | None] = mapped_column(String(80))
