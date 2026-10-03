"""Paging parameters and the `Page<T>` response (API_SURFACE.md § 0)."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Query
from pydantic import BaseModel

MAX_PAGE_SIZE = 200
DEFAULT_PAGE_SIZE = 50


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
    """FastAPI dependency reading `?page&size`."""
    return PageParams(page=page, size=size)


class Page[T](BaseModel):
    """One page of a list."""

    items: list[T]
    page: int
    size: int
    total: int
