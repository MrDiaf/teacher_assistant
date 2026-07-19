import enum
import uuid

from sqlalchemy import Enum, ForeignKey, String, Text, Uuid
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
    COMPLETED = "completed"
    FAILED = "failed"


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
    safe_error: Mapped[str | None] = mapped_column(Text)

    conversation: Mapped[AssistantConversation] = relationship(back_populates="jobs")
