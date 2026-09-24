import pytest

from app.module_host import (
    MODULE_HOST_ENV,
    ModuleHostError,
    assemble_module_host,
    create_module_host,
    create_module_host_from_environment,
)


def test_documents_host_uses_dependency_closed_real_entries_without_other_hooks() -> None:
    entries = assemble_module_host("documents")

    assert [entry.id for entry in entries] == ["platform", "documents"]
    assert [
        contribution.id for entry in entries for contribution in entry.lifecycle
    ] == ["codex-auth", "document-storage-root"]
    assert [contribution.id for entry in entries for contribution in entry.routers] == [
        "ai-models",
        "diagnostics",
        "system-health",
        "documents",
    ]


def test_documents_host_mounts_real_routes_and_omits_unselected_feature_routes() -> None:
    application = create_module_host("documents")
    paths = {route.path for route in application.routes}

    assert "/health" in paths
    assert "/api/v1/document-projects" in paths
    assert "/api/v1/calendars" not in paths
    assert "/api/v1/courses" not in paths
    assert "/api/v1/inbox" not in paths
    assert "/api/v1/assistant/conversations" not in paths


@pytest.mark.parametrize("module_id", ["", "calendar", "unknown", "../documents"])
def test_module_host_rejects_unapproved_module_ids(module_id: str) -> None:
    with pytest.raises(ModuleHostError, match="unsupported module host"):
        assemble_module_host(module_id)


def test_environment_factory_requires_an_explicit_supported_module(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(MODULE_HOST_ENV, raising=False)
    with pytest.raises(ModuleHostError, match=MODULE_HOST_ENV):
        create_module_host_from_environment()

    monkeypatch.setenv(MODULE_HOST_ENV, "documents")
    application = create_module_host_from_environment()
    assert "/api/v1/document-projects" in {route.path for route in application.routes}
