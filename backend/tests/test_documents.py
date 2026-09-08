import io
import os
import uuid
import zipfile
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.documents.service import DocumentService


async def create_project(client: AsyncClient, title: str = "Research notes") -> dict:
    response = await client.post("/api/v1/document-projects", json={"title": title})
    assert response.status_code == 201, response.text
    return response.json()


async def create_tag(client: AsyncClient, name: str = "Research", color: str = "#f4c75f") -> dict:
    response = await client.post("/api/v1/document-tags", json={"name": name, "color": color})
    assert response.status_code == 201, response.text
    return response.json()


async def test_project_crud_search_and_private_initial_source(client: AsyncClient) -> None:
    first = await create_project(client, "  Linear Algebra  ")
    second = await create_project(client, "Teaching outline")
    assert first["title"] == "Linear Algebra"
    assert uuid.UUID(first["id"])
    assert first["tags"] == []

    root = get_settings().document_storage_root
    project_root = root / first["id"]
    assert (
        (project_root / "source" / "main.tex")
        .read_text(encoding="utf-8")
        .startswith("\\documentclass")
    )
    assert (project_root / "build").is_dir()
    assert project_root.stat().st_mode & 0o077 == 0
    assert (project_root / "source" / "main.tex").stat().st_mode & 0o077 == 0

    searched = await client.get("/api/v1/document-projects", params={"search": "algebra"})
    assert searched.status_code == 200
    assert [item["id"] for item in searched.json()] == [first["id"]]

    renamed = await client.patch(
        f"/api/v1/document-projects/{first['id']}", json={"title": "Algebra handout"}
    )
    assert renamed.status_code == 200
    assert renamed.json()["title"] == "Algebra handout"
    assert (root / first["id"]).is_dir()
    assert not (root / "Algebra handout").exists()

    listed = await client.get("/api/v1/document-projects")
    assert {item["id"] for item in listed.json()} == {first["id"], second["id"]}


async def test_many_to_many_tags_filter_and_case_normalized_uniqueness(
    client: AsyncClient,
) -> None:
    first = await create_project(client, "First")
    second = await create_project(client, "Second")
    research = await create_tag(client, "  Research  ", "#123456")
    urgent = await create_tag(client, "Urgent", "#abcdef")

    for project_id, tag_id in (
        (first["id"], research["id"]),
        (second["id"], research["id"]),
        (first["id"], urgent["id"]),
    ):
        response = await client.put(f"/api/v1/document-projects/{project_id}/tags/{tag_id}")
        assert response.status_code == 200

    filtered = await client.get(
        "/api/v1/document-projects", params={"search": "first", "tag_id": research["id"]}
    )
    assert [item["id"] for item in filtered.json()] == [first["id"]]
    assert {tag["name"] for tag in filtered.json()[0]["tags"]} == {"Research", "Urgent"}

    tags = await client.get("/api/v1/document-tags")
    counts = {tag["name"]: tag["project_count"] for tag in tags.json()}
    assert counts == {"Research": 2, "Urgent": 1}

    duplicate = await client.post(
        "/api/v1/document-tags", json={"name": "research", "color": "#000000"}
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "document_tag_conflict"

    updated = await client.patch(
        f"/api/v1/document-tags/{urgent['id']}",
        json={"name": "Priority", "color": "#654321"},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Priority"

    unassigned = await client.delete(f"/api/v1/document-projects/{first['id']}/tags/{urgent['id']}")
    assert unassigned.status_code == 200
    assert [tag["name"] for tag in unassigned.json()["tags"]] == ["Research"]

    deleted_tag = await client.delete(f"/api/v1/document-tags/{research['id']}")
    assert deleted_tag.status_code == 204
    assert (await client.get(f"/api/v1/document-projects/{first['id']}")).status_code == 200
    assert (get_settings().document_storage_root / first["id"] / "source" / "main.tex").is_file()


async def test_downloads_are_source_only_bounded_and_deterministic(client: AsyncClient) -> None:
    project = await create_project(client)
    project_root = get_settings().document_storage_root / project["id"]
    (project_root / "source" / "chapter.tex").write_text("chapter", encoding="utf-8")
    (project_root / "build" / "private.log").write_text("not for download", encoding="utf-8")

    main = await client.get(f"/api/v1/document-projects/{project['id']}/main.tex")
    first_zip = await client.get(f"/api/v1/document-projects/{project['id']}/source.zip")
    second_zip = await client.get(f"/api/v1/document-projects/{project['id']}/source.zip")
    assert main.status_code == 200
    assert main.headers["content-disposition"] == 'attachment; filename="main.tex"'
    assert main.headers["cache-control"] == "private, no-store"
    assert main.headers["x-content-type-options"] == "nosniff"
    assert first_zip.status_code == 200
    assert first_zip.headers["cache-control"] == "private, no-store"
    assert first_zip.content == second_zip.content
    with zipfile.ZipFile(io.BytesIO(first_zip.content)) as archive:
        assert archive.namelist() == ["chapter.tex", "main.tex"]
        assert archive.read("chapter.tex") == b"chapter"
        assert all(
            "build" not in name and not name.startswith("/") and ".." not in name
            for name in archive.namelist()
        )


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="symlinks are unavailable")
async def test_storage_disagreement_and_links_fail_without_exposure(client: AsyncClient) -> None:
    project = await create_project(client)
    tag = await create_tag(client)
    main = get_settings().document_storage_root / project["id"] / "source" / "main.tex"
    outside = main.parents[3] / "outside-secret.tex"
    outside.write_text("secret", encoding="utf-8")
    main.unlink()
    main.symlink_to(outside)

    response = await client.get(f"/api/v1/document-projects/{project['id']}/source.zip")
    detail = await client.get(f"/api/v1/document-projects/{project['id']}")
    assignment = await client.put(f"/api/v1/document-projects/{project['id']}/tags/{tag['id']}")
    deletion = await client.delete(f"/api/v1/document-projects/{project['id']}")
    assert response.status_code == detail.status_code == assignment.status_code == 409
    assert deletion.status_code == 409
    assert response.json()["code"] == "document_storage_mismatch"
    assert "outside" not in response.text
    assert str(get_settings().document_storage_root) not in response.text
    assert outside.read_text(encoding="utf-8") == "secret"


async def test_hard_links_and_special_source_files_are_rejected(client: AsyncClient) -> None:
    project = await create_project(client)
    source = get_settings().document_storage_root / project["id"] / "source"
    alias = source / "alias.tex"
    os.link(source / "main.tex", alias)

    hard_linked = await client.get(f"/api/v1/document-projects/{project['id']}/source.zip")
    assert hard_linked.status_code == 409
    assert hard_linked.json()["code"] == "document_storage_mismatch"

    alias.unlink()
    fifo = source / "compiler.pipe"
    os.mkfifo(fifo)
    special = await client.get(f"/api/v1/document-projects/{project['id']}/source.zip")
    assert special.status_code == 409
    assert special.json()["code"] == "document_storage_mismatch"


async def test_delete_quarantines_exact_uuid_and_restores_on_database_failure(
    client: AsyncClient, session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = await create_project(client, "Delete safely")
    project_id = uuid.UUID(project["id"])
    root = get_settings().document_storage_root
    service = DocumentService(session)
    monkeypatch.setattr(session, "commit", AsyncMock(side_effect=RuntimeError("database failed")))

    with pytest.raises(RuntimeError, match="database failed"):
        await service.delete_project(project_id)
    assert (root / project["id"] / "source" / "main.tex").is_file()
    assert list((root / ".trash").iterdir()) == []

    deleted = await client.delete(f"/api/v1/document-projects/{project['id']}")
    assert deleted.status_code == 204
    assert not (root / project["id"]).exists()
    assert list((root / ".trash").iterdir()) == []
    missing = await client.get(f"/api/v1/document-projects/{project['id']}")
    assert missing.status_code == 404


async def test_creation_removes_new_source_tree_when_database_commit_fails(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = get_settings().document_storage_root
    service = DocumentService(session)
    monkeypatch.setattr(session, "commit", AsyncMock(side_effect=RuntimeError("database failed")))

    with pytest.raises(RuntimeError, match="database failed"):
        await service.create_project("Rollback creation")

    assert [path for path in root.iterdir() if path.name != ".trash"] == []


async def test_document_validation_and_unknown_ids_fail_safely(client: AsyncClient) -> None:
    blank = await client.post("/api/v1/document-projects", json={"title": "   "})
    extra = await client.post(
        "/api/v1/document-projects", json={"title": "Valid", "storage_path": "/tmp/private"}
    )
    bad_color = await client.post("/api/v1/document-tags", json={"name": "Tag", "color": "red"})
    malformed = await client.get("/api/v1/document-projects/../../etc/passwd")
    missing = await client.get(f"/api/v1/document-projects/{uuid.uuid4()}")
    assert blank.status_code == extra.status_code == bad_color.status_code == 422
    assert malformed.status_code in {404, 422}
    assert missing.status_code == 404
