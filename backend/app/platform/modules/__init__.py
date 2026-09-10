"""Typed module registration contract and production catalog."""

from app.platform.modules.catalog import module_catalog
from app.platform.modules.contract import (
    ModuleCatalog,
    ModuleContractError,
    ModuleContributions,
    ModuleDependency,
    ModuleId,
    ModuleRegistration,
    OrderedContribution,
    PageId,
    parse_module_catalog,
)

__all__ = [
    "ModuleCatalog",
    "ModuleContractError",
    "ModuleContributions",
    "ModuleDependency",
    "ModuleId",
    "ModuleRegistration",
    "OrderedContribution",
    "PageId",
    "module_catalog",
    "parse_module_catalog",
]
