from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.calendar.models import enum_values
from app.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.integrations.models import IntegrationConnection


class MailAddressKind(str, enum.Enum):
    FROM = "from"
    REPLY_TO = "reply_to"
    TO = "to"
    CC = "cc"


class MailMessage(TimestampMixin, Base):
    __tablename__ = "mail_messages"
    __table_args__ = (
        UniqueConstraint(
            "mailbox_identity",
            "remote_uid_validity",
            "remote_uid",
            name="uq_mail_messages_remote_identity",
        ),
        CheckConstraint("remote_uid > 0", name="ck_mail_messages_uid_positive"),
        Index("ix_mail_messages_source_date", "source_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    connection_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("mail_integration_connections.id", ondelete="SET NULL"), index=True
    )
    mailbox_identity: Mapped[str] = mapped_column(String(64), nullable=False)
    remote_uid_validity: Mapped[int] = mapped_column(BigInteger, nullable=False)
    remote_uid: Mapped[int] = mapped_column(BigInteger, nullable=False)
    message_id: Mapped[str | None] = mapped_column(String(998))
    in_reply_to: Mapped[str | None] = mapped_column(String(998))
    thread_references: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    subject: Mapped[str] = mapped_column(String(998), nullable=False)
    source_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    body_text: Mapped[str] = mapped_column(Text, nullable=False)
    body_html: Mapped[str | None] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    forwarded_unverified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    connection: Mapped[IntegrationConnection | None] = relationship(back_populates="messages")
    addresses: Mapped[list[MailAddress]] = relationship(
        back_populates="message", cascade="all, delete-orphan", passive_deletes=True
    )
    attachments: Mapped[list[MailAttachment]] = relationship(
        back_populates="message", cascade="all, delete-orphan", passive_deletes=True
    )


class MailAddress(Base):
    __tablename__ = "mail_addresses"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    message_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("mail_messages.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[MailAddressKind] = mapped_column(
        Enum(
            MailAddressKind,
            values_callable=enum_values,
            native_enum=False,
            create_constraint=True,
            length=16,
            name="mail_address_kind",
        ),
        nullable=False,
    )
    display_name: Mapped[str | None] = mapped_column(String(320))
    address: Mapped[str] = mapped_column(String(320), nullable=False)
    position: Mapped[int] = mapped_column(nullable=False)

    message: Mapped[MailMessage] = relationship(back_populates="addresses")


class MailAttachment(Base):
    __tablename__ = "mail_attachments"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    message_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("mail_messages.id", ondelete="CASCADE"), nullable=False, index=True
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    content_hash: Mapped[str | None] = mapped_column(String(64))
    storage_path: Mapped[str | None] = mapped_column(String(96), unique=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    omission_reason: Mapped[str | None] = mapped_column(String(240))

    message: Mapped[MailMessage] = relationship(back_populates="attachments")


class MailQuarantine(TimestampMixin, Base):
    __tablename__ = "mail_quarantines"
    __table_args__ = (
        UniqueConstraint(
            "mailbox_identity",
            "remote_uid_validity",
            "remote_uid",
            name="uq_mail_quarantine_remote_identity",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    connection_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("mail_integration_connections.id", ondelete="CASCADE"),
        nullable=False,
    )
    mailbox_identity: Mapped[str] = mapped_column(String(64), nullable=False)
    remote_uid_validity: Mapped[int] = mapped_column(BigInteger, nullable=False)
    remote_uid: Mapped[int] = mapped_column(BigInteger, nullable=False)
    safe_error_code: Mapped[str] = mapped_column(String(80), nullable=False)
    safe_error: Mapped[str] = mapped_column(String(240), nullable=False)

    connection: Mapped[IntegrationConnection] = relationship(back_populates="quarantines")


class MailCleanupAudit(TimestampMixin, Base):
    __tablename__ = "mail_cleanup_audits"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    deleted_message_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    quarantine_token: Mapped[str | None] = mapped_column(String(96))
    safe_error: Mapped[str | None] = mapped_column(String(240))
