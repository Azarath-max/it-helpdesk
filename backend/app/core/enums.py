"""Small helpers shared by ORM enum columns."""

import enum


def enum_values(enum_cls: type[enum.Enum]) -> list[str]:
    """Store the value of each enum member, not its Python name."""
    return [str(member.value) for member in enum_cls]
