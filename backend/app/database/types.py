"""Small database type helpers shared by module-owned model metadata."""

import enum


def enum_values(enum_type: type[enum.Enum]) -> list[str]:
    """Persist string enum values instead of Python member names."""

    return [member.value for member in enum_type]
