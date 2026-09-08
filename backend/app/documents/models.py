import uuid

from sqlalchemy import CheckConstraint, Column, ForeignKey, Index, String, Table, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin

document_project_tags = Table(
    "document_project_tags",
    Base.metadata,
    Column(
        "project_id",
        Uuid,
        ForeignKey("document_projects.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "tag_id",
        Uuid,
        ForeignKey("document_tags.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Index("ix_document_project_tags_tag_id", "tag_id"),
)


class DocumentProject(TimestampMixin, Base):
    __tablename__ = "document_projects"
    __table_args__ = (
        CheckConstraint("btrim(title) <> ''", name="ck_document_projects_title_not_blank"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    tags: Mapped[list["DocumentTag"]] = relationship(
        secondary=document_project_tags,
        back_populates="projects",
        lazy="selectin",
        order_by="DocumentTag.name_normalized",
    )


class DocumentTag(TimestampMixin, Base):
    __tablename__ = "document_tags"
    __table_args__ = (
        CheckConstraint("btrim(name) <> ''", name="ck_document_tags_name_not_blank"),
        CheckConstraint("color ~ '^#[0-9A-Fa-f]{6}$'", name="ck_document_tags_color_hex"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    name_normalized: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    color: Mapped[str] = mapped_column(String(7), nullable=False)
    projects: Mapped[list[DocumentProject]] = relationship(
        secondary=document_project_tags,
        back_populates="tags",
        lazy="selectin",
    )

    @property
    def project_count(self) -> int:
        return len(self.projects)
