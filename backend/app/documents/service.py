import uuid
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.documents.errors import DocumentTagConflictError
from app.documents.models import DocumentProject, DocumentTag
from app.documents.repository import DocumentRepository
from app.documents.storage import DocumentStorage


class DocumentService:
    def __init__(self, session: AsyncSession, storage: DocumentStorage | None = None) -> None:
        settings = get_settings()
        self.session = session
        self.repository = DocumentRepository(session)
        self.storage = storage or DocumentStorage(
            settings.document_storage_root,
            settings.document_max_source_bytes,
        )

    async def list_projects(
        self, search: str | None = None, tag_id: uuid.UUID | None = None
    ) -> list[DocumentProject]:
        if tag_id is not None:
            await self.repository.get_tag(tag_id)
        return await self.repository.list_projects(search, tag_id)

    async def get_project(self, project_id: uuid.UUID) -> DocumentProject:
        project = await self.repository.get_project(project_id)
        await self.storage.validate_project(project_id)
        return project

    async def create_project(self, title: str) -> DocumentProject:
        project_id = uuid.uuid4()
        project = await self.repository.create_project(project_id, title)
        storage_created = False
        try:
            await self.storage.create_project(project_id)
            storage_created = True
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            if storage_created:
                await self.storage.remove_created_project(project_id)
            raise
        return await self.repository.get_project(project.id)

    async def rename_project(self, project_id: uuid.UUID, title: str) -> DocumentProject:
        await self.storage.validate_project(project_id)
        project = await self.repository.rename_project(project_id, title)
        await self.session.commit()
        return await self.repository.get_project(project.id)

    async def delete_project(self, project_id: uuid.UUID) -> None:
        await self.repository.get_project(project_id, for_update=True)
        quarantine = await self.storage.quarantine_project(project_id)
        try:
            await self.repository.delete_project(project_id)
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            await self.storage.restore(quarantine)
            raise
        await self.storage.purge(quarantine)

    async def list_tags(self) -> list[DocumentTag]:
        return await self.repository.list_tags()

    async def create_tag(self, values: dict[str, Any]) -> DocumentTag:
        values["name_normalized"] = self._normalize_tag_name(values["name"])
        try:
            tag = await self.repository.create_tag(values)
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise DocumentTagConflictError() from exc
        return await self.repository.get_tag(tag.id)

    async def update_tag(self, tag_id: uuid.UUID, changes: dict[str, Any]) -> DocumentTag:
        if "name" in changes:
            changes["name_normalized"] = self._normalize_tag_name(changes["name"])
        try:
            tag = await self.repository.update_tag(tag_id, changes)
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise DocumentTagConflictError() from exc
        return await self.repository.get_tag(tag.id)

    async def delete_tag(self, tag_id: uuid.UUID) -> None:
        await self.repository.delete_tag(tag_id)
        await self.session.commit()

    async def assign_tag(self, project_id: uuid.UUID, tag_id: uuid.UUID) -> DocumentProject:
        await self.storage.validate_project(project_id)
        project = await self.repository.assign_tag(project_id, tag_id)
        await self.session.commit()
        return await self.repository.get_project(project.id)

    async def unassign_tag(self, project_id: uuid.UUID, tag_id: uuid.UUID) -> DocumentProject:
        await self.storage.validate_project(project_id)
        project = await self.repository.unassign_tag(project_id, tag_id)
        await self.session.commit()
        return await self.repository.get_project(project.id)

    async def main_tex(self, project_id: uuid.UUID) -> bytes:
        await self.repository.get_project(project_id)
        return await self.storage.read_main_tex(project_id)

    async def source_zip(self, project_id: uuid.UUID) -> bytes:
        await self.repository.get_project(project_id)
        return await self.storage.build_source_zip(project_id)

    @staticmethod
    def _normalize_tag_name(name: str) -> str:
        return name.casefold()
