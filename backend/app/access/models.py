from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin


class AccessPassword(TimestampMixin, Base):
    """The single owner password. Absent row means access control is off."""

    __tablename__ = "access_password"
    __table_args__ = (CheckConstraint("id = 1", name="ck_access_password_single_row"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    # Rotated with every password change so earlier sign-in cookies stop working.
    session_secret: Mapped[str] = mapped_column(String(128), nullable=False)


class AccessLoginThrottle(TimestampMixin, Base):
    """Failed sign-in attempts for one client address (IPv4 or IPv6 /64)."""

    __tablename__ = "access_login_throttles"

    client_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    failed_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
