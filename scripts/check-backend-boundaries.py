#!/usr/bin/env python3
"""Reject new backend imports across Teacher Assistant module boundaries."""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path


def _matches(value: str, prefix: str) -> bool:
    return value == prefix or value.startswith(f"{prefix}.")


def _owner(value: str, mappings: list[dict[str, str]]) -> str | None:
    matches = [item for item in mappings if _matches(value, item["prefix"])]
    if not matches:
        return None
    return max(matches, key=lambda item: len(item["prefix"]))["owner"]


def _assert_acyclic(dependencies: dict[str, list[str]]) -> list[str]:
    errors: list[str] = []
    visiting: list[str] = []
    visited: set[str] = set()

    def visit(owner: str) -> None:
        if owner in visiting:
            start = visiting.index(owner)
            errors.append("dependency cycle: " + " -> ".join(visiting[start:] + [owner]))
            return
        if owner in visited:
            return
        visiting.append(owner)
        for dependency in dependencies.get(owner, []):
            if dependency not in dependencies:
                errors.append(f"{owner} declares unknown dependency {dependency}")
            else:
                visit(dependency)
        visiting.pop()
        visited.add(owner)

    for owner in dependencies:
        visit(owner)
    return sorted(set(errors))


def _imports(path: Path, importer_module: str) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            imported = node.module or ""
            if node.level:
                package = importer_module.split(".")[:-1]
                keep = len(package) - (node.level - 1)
                imported = ".".join(package[:keep] + ([imported] if imported else []))
            if imported.startswith("app."):
                imports.add(imported)
        elif isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names if alias.name.startswith("app."))
    return imports


def check(repo: Path, source_root: Path, *, require_current_exceptions: bool) -> list[str]:
    config = json.loads((repo / "architecture/module-boundaries.json").read_text())
    backend = config["backend"]
    mappings = backend["path_owners"]
    allowed_platform = backend["allowed_platform_imports"]
    exceptions = {
        (item["importer"], item["imported"]): item["remove_in"]
        for item in backend["legacy_exceptions"]
    }
    seen: set[tuple[str, str]] = set()
    errors = _assert_acyclic(config["declared_dependencies"])

    for path in sorted(source_root.glob("app/**/*.py")):
        relative_to_source = path.relative_to(source_root).with_suffix("")
        importer_module = ".".join(relative_to_source.parts)
        importer_owner = _owner(importer_module, mappings)
        if importer_owner is None:
            errors.append(f"unowned backend file: {path.relative_to(repo)}")
            continue
        importer_path = path.relative_to(repo).as_posix()
        for imported in sorted(_imports(path, importer_module)):
            imported_owner = _owner(imported, mappings)
            if imported_owner is None:
                errors.append(f"unowned backend import: {importer_path} -> {imported}")
                continue
            if imported_owner == importer_owner:
                continue
            if imported_owner == "platform" and any(
                _matches(imported, prefix) for prefix in allowed_platform
            ):
                continue
            key = (importer_path, imported)
            if key in exceptions:
                seen.add(key)
                continue
            errors.append(
                f"forbidden backend import: {importer_path} ({importer_owner}) -> "
                f"{imported} ({imported_owner})"
            )

    if require_current_exceptions:
        for importer, imported in sorted(set(exceptions) - seen):
            errors.append(f"stale backend exception: {importer} -> {imported}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--source-root", type=Path, default=Path("backend"))
    parser.add_argument("--allow-stale-exceptions", action="store_true")
    args = parser.parse_args()
    repo = args.repo.resolve()
    source_root = args.source_root
    if not source_root.is_absolute():
        source_root = repo / source_root
    errors = check(
        repo,
        source_root.resolve(),
        require_current_exceptions=not args.allow_stale_exceptions,
    )
    if errors:
        print("Backend module-boundary check failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("Backend module-boundary check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
