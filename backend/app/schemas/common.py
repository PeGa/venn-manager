"""Base models and shared field types (API_SURFACE.md § 0, § 12)."""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StringConstraints
from pydantic.alias_generators import to_camel

from app.auth.passwords import PASSWORD_MAX, PASSWORD_MIN

CENTS_LIMIT = 9_999_999_999

Cents = Annotated[StrictInt, Field(ge=-CENTS_LIMIT, le=CENTS_LIMIT)]
Password = Annotated[
    str,
    StringConstraints(strict=True, min_length=PASSWORD_MIN, max_length=PASSWORD_MAX),
]


class ApiModel(BaseModel):
    """Response models. Serialized with camelCase field names."""

    model_config = ConfigDict(
        alias_generator=to_camel, populate_by_name=True, serialize_by_alias=True
    )


class InputModel(ApiModel):
    """Request bodies. Unknown fields are rejected; strings are trimmed."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
