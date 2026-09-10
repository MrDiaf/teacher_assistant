"""Metadata-only module registration and dependency contract.

The contract deliberately contains no import paths, callables, or executable
names. Application assembly attaches explicitly imported code in a separate
step.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Literal

type ModuleId = Literal["platform", "calendar", "courses", "inbox", "documents", "assistant"]
type PageId = Literal[
    "dashboard",
    "calendar",
    "courses",
    "inbox",
    "documents",
    "study-plan",
    "assistant",
    "settings",
]

_IDENTIFIER_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")


class ModuleContractError(ValueError):
    """Raised when a module catalog violates the common contract."""


@dataclass(frozen=True, slots=True)
class OrderedContribution:
    id: str
    label: str
    order: int


@dataclass(frozen=True, slots=True)
class ModuleDependency:
    id: str
    requires: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ModuleContributions:
    routes: tuple[str, ...]
    pages: tuple[OrderedContribution, ...]
    settings_panels: tuple[OrderedContribution, ...]
    lifecycle: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ModuleRegistration:
    id: str
    display_name: str
    order: int
    enabled_by_default: bool
    capabilities: tuple[str, ...]
    dependencies: tuple[ModuleDependency, ...]
    contributions: ModuleContributions


class ModuleCatalog:
    """Validated, deterministic collection of module metadata."""

    def __init__(self, registrations: Iterable[ModuleRegistration]) -> None:
        ordered = tuple(sorted(registrations, key=lambda registration: registration.order))
        _validate_registrations(ordered)
        self._registrations = ordered
        self._by_id = MappingProxyType(
            {registration.id: registration for registration in self._registrations}
        )

    @property
    def registrations(self) -> tuple[ModuleRegistration, ...]:
        return self._registrations

    def get(self, module_id: str) -> ModuleRegistration | None:
        """Return known static metadata; arbitrary input never resolves code."""

        return self._by_id.get(module_id)


def parse_module_catalog(payload: object) -> ModuleCatalog:
    """Parse and validate a JSON-compatible catalog payload."""

    catalog = _mapping(payload, "catalog", {"schema_version", "registrations"})
    schema_version = _integer(catalog["schema_version"], "catalog.schema_version")
    if schema_version != 1:
        raise ModuleContractError("catalog.schema_version must be 1")

    raw_registrations = _sequence(catalog["registrations"], "catalog.registrations")
    registrations = tuple(
        _parse_registration(value, f"catalog.registrations[{index}]")
        for index, value in enumerate(raw_registrations)
    )
    return ModuleCatalog(registrations)


def _parse_registration(value: object, path: str) -> ModuleRegistration:
    raw = _mapping(
        value,
        path,
        {
            "id",
            "display_name",
            "order",
            "enabled_by_default",
            "capabilities",
            "dependencies",
            "contributions",
        },
    )
    dependencies = _sequence(raw["dependencies"], f"{path}.dependencies")
    contributions = _mapping(
        raw["contributions"],
        f"{path}.contributions",
        {"routes", "pages", "settings_panels", "lifecycle"},
    )
    return ModuleRegistration(
        id=_identifier(raw["id"], f"{path}.id"),
        display_name=_non_empty_string(raw["display_name"], f"{path}.display_name"),
        order=_integer(raw["order"], f"{path}.order"),
        enabled_by_default=_boolean(raw["enabled_by_default"], f"{path}.enabled_by_default"),
        capabilities=_identifier_sequence(raw["capabilities"], f"{path}.capabilities"),
        dependencies=tuple(
            _parse_dependency(item, f"{path}.dependencies[{index}]")
            for index, item in enumerate(dependencies)
        ),
        contributions=ModuleContributions(
            routes=_identifier_sequence(contributions["routes"], f"{path}.contributions.routes"),
            pages=_parse_ordered_contributions(
                contributions["pages"], f"{path}.contributions.pages"
            ),
            settings_panels=_parse_ordered_contributions(
                contributions["settings_panels"],
                f"{path}.contributions.settings_panels",
            ),
            lifecycle=_identifier_sequence(
                contributions["lifecycle"], f"{path}.contributions.lifecycle"
            ),
        ),
    )


def _parse_dependency(value: object, path: str) -> ModuleDependency:
    raw = _mapping(value, path, {"id", "requires"})
    return ModuleDependency(
        id=_identifier(raw["id"], f"{path}.id"),
        requires=_identifier_sequence(raw["requires"], f"{path}.requires"),
    )


def _parse_ordered_contributions(value: object, path: str) -> tuple[OrderedContribution, ...]:
    values = _sequence(value, path)
    return tuple(
        _parse_ordered_contribution(item, f"{path}[{index}]") for index, item in enumerate(values)
    )


def _parse_ordered_contribution(value: object, path: str) -> OrderedContribution:
    raw = _mapping(value, path, {"id", "label", "order"})
    return OrderedContribution(
        id=_identifier(raw["id"], f"{path}.id"),
        label=_non_empty_string(raw["label"], f"{path}.label"),
        order=_integer(raw["order"], f"{path}.order"),
    )


def _validate_registrations(registrations: tuple[ModuleRegistration, ...]) -> None:
    if not registrations:
        raise ModuleContractError("catalog.registrations must not be empty")

    _unique_values(
        ((registration.id, f"module id {registration.id!r}") for registration in registrations),
        "duplicate module id",
    )
    module_ids = {registration.id for registration in registrations}
    _unique_values(
        ((registration.order, registration.id) for registration in registrations),
        "duplicate module order",
    )

    registrations_by_id = {registration.id: registration for registration in registrations}
    global_contributions: dict[str, dict[str, str]] = {
        "route": {},
        "page": {},
        "settings panel": {},
        "lifecycle": {},
    }
    ordered_contribution_orders: dict[str, dict[int, str]] = {
        "page": {},
        "settings panel": {},
    }

    for registration in registrations:
        _validate_registration_shape(registration)
        dependency_ids: set[str] = set()
        for dependency in registration.dependencies:
            if dependency.id in dependency_ids:
                raise ModuleContractError(
                    f"module {registration.id!r} declares dependency {dependency.id!r} twice"
                )
            dependency_ids.add(dependency.id)
            if dependency.id == registration.id:
                raise ModuleContractError(f"module {registration.id!r} cannot depend on itself")
            provider = registrations_by_id.get(dependency.id)
            if provider is None:
                raise ModuleContractError(
                    f"module {registration.id!r} requires unknown module {dependency.id!r}"
                )
            missing = sorted(set(dependency.requires) - set(provider.capabilities))
            if missing:
                raise ModuleContractError(
                    f"module {registration.id!r} requires capabilities not provided by "
                    f"{dependency.id!r}: {', '.join(missing)}"
                )

        _validate_contribution_ids(
            registration.id,
            "route",
            registration.contributions.routes,
            global_contributions,
        )
        _validate_ordered_contributions(
            registration.id,
            "page",
            registration.contributions.pages,
            global_contributions,
            ordered_contribution_orders,
        )
        _validate_ordered_contributions(
            registration.id,
            "settings panel",
            registration.contributions.settings_panels,
            global_contributions,
            ordered_contribution_orders,
        )
        _validate_contribution_ids(
            registration.id,
            "lifecycle",
            registration.contributions.lifecycle,
            global_contributions,
        )

    _validate_acyclic(registrations, module_ids)


def _validate_registration_shape(registration: ModuleRegistration) -> None:
    _identifier(registration.id, f"module {registration.id!r}.id")
    _non_empty_string(registration.display_name, f"module {registration.id!r}.display_name")
    _integer(registration.order, f"module {registration.id!r}.order")
    _boolean(registration.enabled_by_default, f"module {registration.id!r}.enabled_by_default")
    _unique_identifiers(registration.capabilities, f"module {registration.id!r}.capabilities")
    for dependency in registration.dependencies:
        _identifier(dependency.id, f"module {registration.id!r}.dependency.id")
        _unique_identifiers(
            dependency.requires,
            f"module {registration.id!r}.dependency[{dependency.id!r}].requires",
        )


def _validate_ordered_contributions(
    module_id: str,
    kind: str,
    contributions: tuple[OrderedContribution, ...],
    global_contributions: dict[str, dict[str, str]],
    global_orders: dict[str, dict[int, str]],
) -> None:
    for contribution in contributions:
        _identifier(contribution.id, f"module {module_id!r} {kind} id")
        _non_empty_string(contribution.label, f"module {module_id!r} {kind} label")
        _integer(contribution.order, f"module {module_id!r} {kind} order")
        _record_unique_contribution(module_id, kind, contribution.id, global_contributions)
        existing = global_orders[kind].get(contribution.order)
        if existing is not None:
            raise ModuleContractError(
                f"duplicate {kind} order {contribution.order}: {existing!r} and {contribution.id!r}"
            )
        global_orders[kind][contribution.order] = contribution.id


def _validate_contribution_ids(
    module_id: str,
    kind: str,
    contribution_ids: tuple[str, ...],
    global_contributions: dict[str, dict[str, str]],
) -> None:
    _unique_identifiers(contribution_ids, f"module {module_id!r}.{kind}")
    for contribution_id in contribution_ids:
        _record_unique_contribution(module_id, kind, contribution_id, global_contributions)


def _record_unique_contribution(
    module_id: str,
    kind: str,
    contribution_id: str,
    global_contributions: dict[str, dict[str, str]],
) -> None:
    existing = global_contributions[kind].get(contribution_id)
    if existing is not None:
        raise ModuleContractError(
            f"duplicate {kind} id {contribution_id!r} in modules {existing!r} and {module_id!r}"
        )
    global_contributions[kind][contribution_id] = module_id


def _validate_acyclic(registrations: tuple[ModuleRegistration, ...], module_ids: set[str]) -> None:
    graph = {
        registration.id: tuple(dependency.id for dependency in registration.dependencies)
        for registration in registrations
    }
    visited: set[str] = set()
    visiting: list[str] = []

    def visit(module_id: str) -> None:
        if module_id in visited:
            return
        if module_id in visiting:
            cycle_start = visiting.index(module_id)
            cycle = [*visiting[cycle_start:], module_id]
            raise ModuleContractError(f"module dependency cycle: {' -> '.join(cycle)}")
        visiting.append(module_id)
        for dependency_id in graph[module_id]:
            if dependency_id in module_ids:
                visit(dependency_id)
        visiting.pop()
        visited.add(module_id)

    for registration in registrations:
        visit(registration.id)


def _mapping(value: object, path: str, expected_keys: set[str]) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ModuleContractError(f"{path} must be an object")
    actual_keys = set(value)
    missing = sorted(expected_keys - actual_keys)
    unknown = sorted(actual_keys - expected_keys)
    if missing or unknown:
        details: list[str] = []
        if missing:
            details.append(f"missing keys: {', '.join(missing)}")
        if unknown:
            details.append(f"unknown keys: {', '.join(unknown)}")
        raise ModuleContractError(f"{path} has invalid fields ({'; '.join(details)})")
    return value


def _sequence(value: object, path: str) -> Sequence[object]:
    if not isinstance(value, list):
        raise ModuleContractError(f"{path} must be an array")
    return value


def _non_empty_string(value: object, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ModuleContractError(f"{path} must be a non-empty string")
    return value


def _identifier(value: object, path: str) -> str:
    candidate = _non_empty_string(value, path)
    if not _IDENTIFIER_PATTERN.fullmatch(candidate):
        raise ModuleContractError(f"{path} must be a lowercase kebab-case identifier")
    return candidate


def _integer(value: object, path: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ModuleContractError(f"{path} must be an integer")
    return value


def _boolean(value: object, path: str) -> bool:
    if not isinstance(value, bool):
        raise ModuleContractError(f"{path} must be a boolean")
    return value


def _identifier_sequence(value: object, path: str) -> tuple[str, ...]:
    values = _sequence(value, path)
    identifiers = tuple(_identifier(item, f"{path}[{index}]") for index, item in enumerate(values))
    _unique_identifiers(identifiers, path)
    return identifiers


def _unique_identifiers(values: tuple[str, ...], path: str) -> None:
    seen: set[str] = set()
    for index, value in enumerate(values):
        _identifier(value, f"{path}[{index}]")
        if value in seen:
            raise ModuleContractError(f"{path} contains duplicate identifier {value!r}")
        seen.add(value)


def _unique_values(values: Iterable[tuple[str | int, str]], message: str) -> set[str | int]:
    seen: set[str | int] = set()
    for value, description in values:
        if value in seen:
            raise ModuleContractError(f"{message}: {description}")
        seen.add(value)
    return seen
