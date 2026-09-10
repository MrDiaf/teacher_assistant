"""Validated production module metadata."""

import json
from pathlib import Path

from app.platform.modules.contract import ModuleCatalog, parse_module_catalog

_CATALOG_PATH = Path(__file__).with_name("catalog.json")


def load_module_catalog(path: Path = _CATALOG_PATH) -> ModuleCatalog:
    return parse_module_catalog(json.loads(path.read_text(encoding="utf-8")))


module_catalog = load_module_catalog()
