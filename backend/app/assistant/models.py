import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
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


class AssistantMessageRole(str, enum.Enum):
    OWNER = "owner"
    ASSISTANT = "assistant"


class AssistantJobStatus(str, enum.Enum):
    QUEUED = "queued"
    PREPARING_CONTEXT = "preparing_context"
    RUNNING = "running"
    VALIDATING = "validating"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AssistantProposalStatus(str, enum.Enum):
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


class AssistantConversation(TimestampMixin, Base):
    __tablename__ = "assistant_conversations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(120), nullable=False, default="Calendar conversation")

    messages: Mapped[list["AssistantMessage"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="AssistantMessage.created_at",
    )
    jobs: Mapped[list["AssistantJob"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    proposals: Mapped[list["AssistantProposal"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class AssistantMessage(TimestampMixin, Base):
    __tablename__ = "assistant_messages"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("assistant_conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[AssistantMessageRole] = mapped_column(
        Enum(
            AssistantMessageRole,
            values_callable=enum_values,
            native_enum=False,
            create_constraint=True,
            length=20,
            name="assistant_message_role",
        ),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    citations: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("assistant_jobs.id", ondelete="SET NULL", use_alter=True),
        nullable=True,
        index=True,
    )

    conversation: Mapped[AssistantConversation] = relationship(back_populates="messages")


class AssistantJob(TimestampMixin, Base):
    __tablename__ = "assistant_jobs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("assistant_conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    owner_message_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("assistant_messages.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    status: Mapped[AssistantJobStatus] = mapped_column(
        Enum(
            AssistantJobStatus,
            values_callable=enum_values,
            native_enum=False,
            create_constraint=True,
            length=32,
            name="assistant_job_status",
        ),
        nullable=False,
        default=AssistantJobStatus.QUEUED,
    )
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    safe_error: Mapped[str | None] = mapped_column(Text)
    safe_error_code: Mapped[str | None] = mapped_column(String(80))
    safe_error_details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    diagnostic_error_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("diagnostic_errors.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    conversation: Mapped[AssistantConversation] = relationship(back_populates="jobs")
    proposals: Mapped[list["AssistantProposal"]] = relationship(
        back_populates="job",
        order_by="AssistantProposal.batch_position",
    )


class AssistantProposal(TimestampMixin, Base):
    __tablename__ = "assistant_proposals"
    __table_args__ = (
        CheckConstraint(
            "batch_position >= 1 AND batch_position <= batch_count",
            name="assistant_proposal_batch_position",
        ),
        CheckConstraint(
            "batch_count >= 1 AND batch_count <= 10",
            name="assistant_proposal_batch_count",
        ),
        UniqueConstraint("job_id", "batch_position", name="uq_assistant_proposal_job_batch"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("assistant_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("assistant_conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[AssistantProposalStatus] = mapped_column(
        Enum(
            AssistantProposalStatus,
            values_callable=enum_values,
            native_enum=False,
            create_constraint=True,
            length=32,
            name="assistant_proposal_status",
        ),
        nullable=False,
        default=AssistantProposalStatus.AWAITING_CONFIRMATION,
    )
    summary: Mapped[str] = mapped_column(String(240), nullable=False)
    batch_position: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    batch_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    actions: Mapped[list[dict]] = mapped_column(JSON, nullable=False)
    baselines: Mapped[list[dict]] = mapped_column(JSON, nullable=False)
    review_items: Mapped[list[dict]] = mapped_column(JSON, nullable=False)
    warnings: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    affected_events: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    result: Mapped[dict | None] = mapped_column(JSON)
    safe_error: Mapped[str | None] = mapped_column(Text)

    conversation: Mapped[AssistantConversation] = relationship(back_populates="proposals")
    job: Mapped[AssistantJob] = relationship(back_populates="proposals")
    action_records: Mapped[list["AssistantProposalAction"]] = relationship(
        back_populates="proposal",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="AssistantProposalAction.position",
    )


class AssistantProposalAction(Base):
    __tablename__ = "assistant_proposal_actions"
    __table_args__ = (
        UniqueConstraint("proposal_id", "position", name="uq_proposal_action_position"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    proposal_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("assistant_proposals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    operation: Mapped[str] = mapped_column(String(40), nullable=False)
    target_calendar_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    target_event_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    result: Mapped[dict | None] = mapped_column(JSON)
    safe_error: Mapped[str | None] = mapped_column(Text)

    proposal: Mapped[AssistantProposal] = relationship(back_populates="action_records")


class AssistantContextAudit(Base):
    __tablename__ = "assistant_context_audits"
    __table_args__ = (
        UniqueConstraint(
            "job_id",
            name="uq_assistant_context_audits_job_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("assistant_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    course_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    note_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    source_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    slide_numbers: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
    requires_clarification: Mapped[bool] = mapped_column(nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
