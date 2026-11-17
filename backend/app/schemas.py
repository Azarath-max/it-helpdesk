"""Shared response schemas and serialization conventions."""

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class APIModel(BaseModel):
    """Base model that exposes camelCase JSON while using snake_case in Python."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        extra="forbid",
    )


class Page[ItemT](APIModel):
    """Offset pagination envelope."""

    items: list[ItemT]
    total: int
    page: int
    page_size: int
