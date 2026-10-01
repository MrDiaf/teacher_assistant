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


def test_calendar_host_uses_real_routes_and_subscription_lifecycle() -> None:
    entries = assemble_module_host("calendar")

    assert [entry.id for entry in entries] == ["platform", "calendar"]
    assert [
        contribution.id for entry in entries for contribution in entry.lifecycle
    ] == ["codex-auth", "ics-subscription-refresh"]
    assert [contribution.id for entry in entries for contribution in entry.routers] == [
        "ai-models",
        "diagnostics",
        "system-health",
        "calendar",
        "calendar-import",
        "calendar-subscription",
    ]

    paths = {route.path for route in create_module_host("calendar").routes}
    assert "/api/v1/calendars" in paths
    assert "/api/v1/events" in paths
    assert "/api/v1/calendar-imports/ics" in paths
    assert "/api/v1/calendar-subscriptions/ics" in paths
    assert "/api/v1/courses" not in paths
    assert "/api/v1/document-projects" not in paths
    assert "/api/v1/assistant/conversations" not in paths


def test_courses_host_closes_over_calendar_and_omits_unrelated_features() -> None:
    entries = assemble_module_host("courses")

    assert [entry.id for entry in entries] == ["platform", "calendar", "courses"]
    assert [
        contribution.id for entry in entries for contribution in entry.lifecycle
    ] == ["codex-auth", "ics-subscription-refresh"]

    paths = {route.path for route in create_module_host("courses").routes}
    assert "/api/v1/courses" in paths
    assert "/api/v1/courses/{course_id}/calendars" in paths
    assert "/api/v1/courses/{course_id}/sources" in paths
    assert "/api/v1/courses/{course_id}/notes" in paths
    assert "/api/v1/notes/{note_id}/summaries" in paths
    assert "/api/v1/notes/prettify" in paths
    assert "/api/v1/calendars" in paths
    assert "/api/v1/ai/models" in paths
    assert "/api/v1/assistant/conversations" not in paths
    assert "/api/v1/inbox" not in paths
    assert "/api/v1/document-projects" not in paths


def test_assistant_host_closes_over_real_calendar_and_courses_providers() -> None:
    entries = assemble_module_host("assistant")

    assert [entry.id for entry in entries] == [
        "platform",
        "calendar",
        "courses",
        "assistant",
    ]
    assert [
        contribution.id for entry in entries for contribution in entry.lifecycle
    ] == ["codex-auth", "ics-subscription-refresh", "assistant-execution"]

    paths = {route.path for route in create_module_host("assistant").routes}
    assert "/api/v1/assistant/conversations" in paths
    assert "/api/v1/assistant/proposals/{proposal_id}/confirm" in paths
    assert "/api/v1/calendars" in paths
    assert "/api/v1/courses" in paths
    assert "/api/v1/ai/auth" in paths
    assert "/api/v1/diagnostics/errors/{error_id}/explain" in paths
    assert "/api/v1/inbox" not in paths
    assert "/api/v1/document-projects" not in paths


def test_documents_host_mounts_real_routes_and_omits_unselected_feature_routes() -> None:
    application = create_module_host("documents")
    paths = {route.path for route in application.routes}

    assert "/health" in paths
    assert "/api/v1/document-projects" in paths
    assert "/api/v1/calendars" not in paths
    assert "/api/v1/courses" not in paths
    assert "/api/v1/inbox" not in paths
    assert "/api/v1/assistant/conversations" not in paths


@pytest.mark.parametrize("module_id", ["", "unknown", "../documents", "calendar,documents"])
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
