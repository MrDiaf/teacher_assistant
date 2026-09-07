from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.calendar.models import enum_values
from app.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.inbox.models import MailMessage, MailQuarantine


class MailTlsMode(str, enum.Enum):
    IMPLICIT = "implicit_tls"
    STARTTLS = "starttls"


class IntegrationStatus(str, enum.Enum):
    CONNECTED = "connected"
    RECONNECT_REQUIRED = "reconnect_required"
    ERROR = "error"


class IntegrationConnection(TimestampMixin, Base):
    __tablename__ = "mail_integration_connections"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    kind: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    host: Mapped[str] = mapped_column(String(253), nullable=False)
    port: Mapped[int] = mapped_column(nullable=False)
    tls_mode: Mapped[MailTlsMode] = mapped_column(
        Enum(
            MailTlsMode,
            values_callable=enum_values,
            native_enum=False,
            create_constraint=True,
            length=24,
            name="mail_tls_mode",
        ),
        nullable=False,
    )
    mailbox: Mapped[str] = mapped_column(String(255), nullable=False)
    username: Mapped[str] = mapped_column(String(320), nullable=False)
    credential_ref: Mapped[str | None] = mapped_column(String(36), unique=True)
    status: Mapped[IntegrationStatus] = mapped_column(
        Enum(
            IntegrationStatus,
            values_callable=enum_values,
            native_enum=False,
            create_constraint=True,
            length=32,
            name="integration_status",
        ),
        nullable=False,
    )

    cursor: Mapped[MailSyncCursor | None] = relationship(
        back_populates="connection", cascade="all, delete-orphan", uselist=False
    )
    messages: Mapped[list[MailMessage]] = relationship(back_populates="connection")
    quarantines: Mapped[list[MailQuarantine]] = relationship(back_populates="connection")


class MailSyncCursor(TimestampMixin, Base):
    __tablename__ = "mail_sync_cursors"

    connection_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("mail_integration_connections.id", ondelete="CASCADE"),
        primary_key=True,
    )
    uid_validity: Mapped[int | None] = mapped_column(BigInteger)
    last_uid: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_check_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    failure_count: Mapped[int] = mapped_column(nullable=False, default=0)
    safe_error_code: Mapped[str | None] = mapped_column(String(80))
    safe_error: Mapped[str | None] = mapped_column(Text)
    source_warning: Mapped[str | None] = mapped_column(Text)

    connection: Mapped[IntegrationConnection] = relationship(back_populates="cursor")
