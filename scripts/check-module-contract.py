#!/usr/bin/env python3
"""Check that both typed module catalogs agree with the ownership manifest."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path


def _load(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--simulate-frontend-drift", action="store_true")
    args = parser.parse_args()
    repo = args.repo.resolve()

    backend_path = repo / "backend/app/platform/modules/catalog.json"
    frontend_path = repo / "frontend/src/platform/modules/catalog.json"
    boundaries_path = repo / "architecture/module-boundaries.json"
    backend = _load(backend_path)
    frontend = _load(frontend_path)
    boundaries = _load(boundaries_path)
    if args.simulate_frontend_drift and isinstance(frontend, dict):
        frontend = copy.deepcopy(frontend)
        registrations = frontend.get("registrations")
        if isinstance(registrations, list) and registrations:
            registrations[0]["display_name"] = "Deliberately invalid fixture"

    errors: list[str] = []
    if backend != frontend:
        errors.append("backend and frontend module catalogs differ")

    if not isinstance(backend, dict) or not isinstance(backend.get("registrations"), list):
        errors.append("backend module catalog does not contain registrations")
    else:
        registrations = backend["registrations"]
        catalog_ids = [registration.get("id") for registration in registrations]
        owner_ids = boundaries.get("owners", []) if isinstance(boundaries, dict) else []
        if set(catalog_ids) != set(owner_ids):
            errors.append(
                "module identities differ from architecture owners: "
                f"catalog={catalog_ids!r}, owners={owner_ids!r}"
            )

        declared_dependencies = (
            boundaries.get("declared_dependencies", {}) if isinstance(boundaries, dict) else {}
        )
        for registration in registrations:
            module_id = registration.get("id")
            dependencies = sorted(
                dependency.get("id") for dependency in registration.get("dependencies", [])
            )
            expected = sorted(declared_dependencies.get(module_id, []))
            if dependencies != expected:
                errors.append(
                    f"dependency drift for {module_id!r}: catalog={dependencies!r}, "
                    f"boundaries={expected!r}"
                )

        expected_entry_ids = set(catalog_ids) - {"platform"}
        for side in ("backend", "frontend"):
            side_config = boundaries.get(side, {}) if isinstance(boundaries, dict) else {}
            public_entries = (
                side_config.get("public_module_entries", {})
                if isinstance(side_config, dict)
                else {}
            )
            if set(public_entries) != expected_entry_ids:
                errors.append(
                    f"{side} public-entry identities differ from catalog: "
                    f"entries={sorted(public_entries)!r}, expected={sorted(expected_entry_ids)!r}"
                )

    if errors:
        for error in errors:
            print(f"Module contract check failed: {error}")
        return 1

    print("Module contract check passed: catalogs, module identities, and dependencies agree.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
