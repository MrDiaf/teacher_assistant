import copy
import json
from pathlib import Path

import pytest

from app.platform.modules.catalog import module_catalog
from app.platform.modules.contract import (
    ModuleContractError,
    parse_module_catalog,
    select_module_catalog,
)

CATALOG_PATH = Path(__file__).parents[1] / "app/platform/modules/catalog.json"


def _catalog_payload() -> dict[str, object]:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def test_production_catalog_has_stable_module_and_page_order() -> None:
    assert [registration.id for registration in module_catalog.registrations] == [
        "platform",
        "calendar",
        "courses",
        "inbox",
        "documents",
        "assistant",
    ]
    pages = sorted(
        (
            page
            for registration in module_catalog.registrations
            for page in registration.contributions.pages
        ),
        key=lambda page: page.order,
    )
    assert [page.id for page in pages] == [
        "dashboard",
        "calendar",
        "courses",
        "inbox",
        "documents",
        "study-plan",
        "assistant",
        "settings",
    ]
    assert module_catalog.get("calendar") is not None
    assert module_catalog.get("browser-controlled-input") is None


@pytest.mark.parametrize(
    ("mutate", "expected_message"),
    [
        (
            lambda payload: payload["registrations"][1].update(
                id=payload["registrations"][0]["id"]
            ),
            "duplicate module id",
        ),
        (
            lambda payload: payload["registrations"][1].update(
                order=payload["registrations"][0]["order"]
            ),
            "duplicate module order",
        ),
        (
            lambda payload: payload["registrations"][1]["dependencies"][0].update(
                id="missing-module"
            ),
            "requires unknown module",
        ),
        (
            lambda payload: payload["registrations"][1]["dependencies"].append(
                copy.deepcopy(payload["registrations"][1]["dependencies"][0])
            ),
            "declares dependency 'platform' twice",
        ),
        (
            lambda payload: payload["registrations"][0]["dependencies"].append(
                {"id": "platform", "requires": ["shell"]}
            ),
            "cannot depend on itself",
        ),
        (
            lambda payload: payload["registrations"][1]["dependencies"][0]["requires"].append(
                "missing-capability"
            ),
            "requires capabilities not provided",
        ),
        (
            lambda payload: payload["registrations"][0]["dependencies"].append(
                {"id": "assistant", "requires": ["api"]}
            ),
            "module dependency cycle",
        ),
        (
            lambda payload: payload["registrations"][1]["contributions"]["routes"].append(
                payload["registrations"][0]["contributions"]["routes"][0]
            ),
            "duplicate route id",
        ),
        (
            lambda payload: payload["registrations"][1]["capabilities"].append(
                payload["registrations"][1]["capabilities"][0]
            ),
            "contains duplicate identifier",
        ),
        (
            lambda payload: payload["registrations"][1]["contributions"]["pages"].append(
                copy.deepcopy(payload["registrations"][1]["contributions"]["pages"][0])
            ),
            "duplicate page id",
        ),
        (
            lambda payload: payload["registrations"][4]["contributions"]["lifecycle"].append(
                payload["registrations"][4]["contributions"]["lifecycle"][0]
            ),
            "contains duplicate identifier",
        ),
        (
            lambda payload: payload["registrations"][1]["contributions"]["pages"][0].update(
                order=payload["registrations"][0]["contributions"]["pages"][0]["order"]
            ),
            "duplicate page order",
        ),
        (
            lambda payload: payload["registrations"][1].update(import_path="app.calendar.entry"),
            "unknown keys: import_path",
        ),
    ],
)
def test_invalid_catalogs_are_rejected(mutate, expected_message: str) -> None:
    payload = copy.deepcopy(_catalog_payload())
    mutate(payload)

    with pytest.raises(ModuleContractError, match=expected_message):
        parse_module_catalog(payload)


def test_parsed_catalog_is_not_affected_by_mutating_input() -> None:
    payload = _catalog_payload()
    catalog = parse_module_catalog(payload)

    payload["registrations"][0]["display_name"] = "Changed"

    assert catalog.registrations[0].display_name == "Platform"


def test_module_selection_includes_transitive_dependencies_in_catalog_order() -> None:
    selected = select_module_catalog(module_catalog, ("documents",))

    assert [registration.id for registration in selected.registrations] == [
        "platform",
        "documents",
    ]


@pytest.mark.parametrize(
    ("module_ids", "message"),
    [
        ((), "must not be empty"),
        (("documents", "documents"), "duplicate"),
        (("unknown",), "unknown module"),
    ],
)
def test_module_selection_rejects_invalid_requests(
    module_ids: tuple[str, ...], message: str
) -> None:
    with pytest.raises(ModuleContractError, match=message):
        select_module_catalog(module_catalog, module_ids)
