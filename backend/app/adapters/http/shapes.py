"""Wire shapes shared by several routers (API_SURFACE.md § 0, § 1).

Shapes used by a single router live in that router's module.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Annotated, Literal
from uuid import UUID

from fastapi import Query
from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StrictInt,
    StringConstraints,
)
from pydantic.alias_generators import to_camel

from app.application.auth import SessionView
from app.domain.errors import validation
from app.domain.members import PASSWORD_MAX, PASSWORD_MIN

CENTS_LIMIT = 9_999_999_999
MAX_PAGE_SIZE = 200
DEFAULT_PAGE_SIZE = 50

ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")

Cents = Annotated[StrictInt, Field(ge=-CENTS_LIMIT, le=CENTS_LIMIT)]


def _iso_date(value: object) -> date:
    if not isinstance(value, str) or not ISO_DATE.fullmatch(value):
        raise ValueError("Dates are YYYY-MM-DD")
    return date.fromisoformat(value)


IsoDate = Annotated[date, BeforeValidator(_iso_date)]
Password = Annotated[
    str,
    StringConstraints(strict=True, min_length=PASSWORD_MIN, max_length=PASSWORD_MAX),
]


def trimmed(max_length: int) -> StringConstraints:
    """Constraints for a trimmed, non-empty string up to *max_length*."""
    return StringConstraints(
        strict=True, strip_whitespace=True, min_length=1, max_length=max_length
    )


class ApiModel(BaseModel):
    """Responses: camelCase on the wire, built from domain views by attribute."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
        from_attributes=True,
    )


class InputModel(ApiModel):
    """Request bodies. Unknown fields are rejected."""

    model_config = ConfigDict(extra="forbid")


def provided(body: BaseModel, nullable: tuple[str, ...] = ()) -> dict[str, object]:
    """The fields a PATCH body actually sent, by Python name.

    An empty body, or `null` for a field that cannot be null, is `VALIDATION`.
    """
    sent = {name: getattr(body, name) for name in body.model_fields_set}
    if not sent:
        raise validation("Nothing to change")
    for name, value in sent.items():
        if value is None and name not in nullable:
            raise validation(f"Invalid {to_camel(name)}", to_camel(name))
    return sent


class PeriodOut(ApiModel):
    month: str
    start: date
    end: date
    today: date
    days_in_month: int


class MemberOut(ApiModel):
    id: UUID
    username: str
    real_name: str
    initial: str
    color: str
    role: Literal["admin", "member"]
    status: Literal["active", "removed"]
    spent_this_month: int


class PreferencesOut(ApiModel):
    language: Literal["en", "es"] | None
    theme: Literal["light", "dark", "system"]


class SessionOut(ApiModel):
    member: MemberOut
    must_change_password: bool
    preferences: PreferencesOut

    @classmethod
    def of(cls, view: SessionView) -> SessionOut:
        """Shape a domain session view."""
        return cls.model_validate(
            {
                "member": view.member,
                "must_change_password": view.must_change_password,
                "preferences": {"language": view.language, "theme": view.theme},
            }
        )


@dataclass(frozen=True)
class PageParams:
    """A validated `page` / `size` pair."""

    page: int
    size: int

    @property
    def offset(self) -> int:
        """Rows to skip before this page."""
        return (self.page - 1) * self.size


def page_params(
    page: int = Query(1, ge=1),
    size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
) -> PageParams:
    """Read `?page&size`."""
    return PageParams(page=page, size=size)


class Page[T](BaseModel):
    """One page of a list."""

    items: list[T]
    page: int
    size: int
    total: int
