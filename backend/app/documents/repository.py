import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.documents.errors import DocumentProjectNotFoundError, DocumentTagNotFoundError
from app.documents.models import DocumentProject, DocumentTag, document_project_tags


class DocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_projects(
        self, search: str | None = None, tag_id: uuid.UUID | None = None
    ) -> list[DocumentProject]:
        statement = select(DocumentProject).options(selectinload(DocumentProject.tags))
        if search:
            statement = statement.where(DocumentProject.title.icontains(search, autoescape=True))
        if tag_id is not None:
            statement = statement.join(document_project_tags).where(
                document_project_tags.c.tag_id == tag_id
            )
        statement = statement.order_by(DocumentProject.updated_at.desc(), DocumentProject.id)
        return list(await self.session.scalars(statement))

    async def get_project(
        self, project_id: uuid.UUID, *, for_update: bool = False
    ) -> DocumentProject:
        statement = (
            select(DocumentProject)
            .where(DocumentProject.id == project_id)
            .options(selectinload(DocumentProject.tags))
        )
        if for_update:
            statement = statement.with_for_update()
        project = await self.session.scalar(statement)
        if project is None:
            raise DocumentProjectNotFoundError()
        return project

    async def create_project(self, project_id: uuid.UUID, title: str) -> DocumentProject:
        project = DocumentProject(id=project_id, title=title)
        self.session.add(project)
        await self.session.flush()
        return project

    async def rename_project(self, project_id: uuid.UUID, title: str) -> DocumentProject:
        project = await self.get_project(project_id, for_update=True)
        project.title = title
        await self.session.flush()
        return project

    async def delete_project(self, project_id: uuid.UUID) -> None:
        project = await self.get_project(project_id, for_update=True)
        await self.session.delete(project)
        await self.session.flush()

    async def list_tags(self) -> list[DocumentTag]:
        statement = (
            select(DocumentTag)
            .options(selectinload(DocumentTag.projects))
            .order_by(DocumentTag.name_normalized, DocumentTag.id)
        )
        return list(await self.session.scalars(statement))

    async def get_tag(self, tag_id: uuid.UUID, *, for_update: bool = False) -> DocumentTag:
        statement = (
            select(DocumentTag)
            .where(DocumentTag.id == tag_id)
            .options(selectinload(DocumentTag.projects))
        )
        if for_update:
            statement = statement.with_for_update()
        tag = await self.session.scalar(statement)
        if tag is None:
            raise DocumentTagNotFoundError()
        return tag

    async def create_tag(self, values: dict[str, Any]) -> DocumentTag:
        tag = DocumentTag(**values)
        self.session.add(tag)
        await self.session.flush()
        return tag

    async def update_tag(self, tag_id: uuid.UUID, changes: dict[str, Any]) -> DocumentTag:
        tag = await self.get_tag(tag_id, for_update=True)
        for key, value in changes.items():
            setattr(tag, key, value)
        await self.session.flush()
        return tag

    async def delete_tag(self, tag_id: uuid.UUID) -> None:
        tag = await self.get_tag(tag_id, for_update=True)
        await self.session.delete(tag)
        await self.session.flush()

    async def assign_tag(self, project_id: uuid.UUID, tag_id: uuid.UUID) -> DocumentProject:
        project = await self.get_project(project_id, for_update=True)
        tag = await self.get_tag(tag_id, for_update=True)
        if all(existing.id != tag.id for existing in project.tags):
            project.tags.append(tag)
            project.updated_at = func.now()
            await self.session.flush()
        return project

    async def unassign_tag(self, project_id: uuid.UUID, tag_id: uuid.UUID) -> DocumentProject:
        project = await self.get_project(project_id, for_update=True)
        await self.get_tag(tag_id)
        project.tags = [tag for tag in project.tags if tag.id != tag_id]
        project.updated_at = func.now()
        await self.session.flush()
        return project
