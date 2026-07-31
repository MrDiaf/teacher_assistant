import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin


class DiagnosticError(TimestampMixin, Base):
    __tablename__ = "diagnostic_errors"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    request_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, nullable=False, index=True, default=uuid.uuid4
    )
    code: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    operation: Mapped[str] = mapped_column(String(240), nullable=False)
    details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    exception_type: Mapped[str | None] = mapped_column(String(120))
    explanation: Mapped[dict | None] = mapped_column(JSON)
    explanation_model: Mapped[str | None] = mapped_column(String(100))
    explained_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    audit_records: Mapped[list["DiagnosticAuditRecord"]] = relationship(
        back_populates="error",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="DiagnosticAuditRecord.created_at",
    )


class DiagnosticAuditRecord(Base):
    __tablename__ = "diagnostic_audit_records"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    error_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("diagnostic_errors.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    action: Mapped[str] = mapped_column(String(60), nullable=False)
    details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    error: Mapped[DiagnosticError] = relationship(back_populates="audit_records")
