"""Pagination maths (API_SURFACE.md § Pagination).

Kept separate from request parsing so the rules are testable without Flask.
"""

from __future__ import annotations

from dataclasses import dataclass

#: The only page sizes the contract defines. `all` is the explicit exception.
ALLOWED_PAGE_SIZES = (10, 20, 50)
DEFAULT_PAGE_SIZE = 10
ALL = "all"


@dataclass(frozen=True)
class Pagination:
    """A resolved page request. `per_page` is None for `q=all`."""

    page: int
    per_page: int | None


def meta_for(total: int, pagination: Pagination) -> dict[str, int]:
    """Build the `meta` block for a list response.

    With `q=all`, `per_page` equals the total count and `total_pages` is 1.
    An empty list still reports one page, so the frontend never divides by zero.
    """
    if pagination.per_page is None:
        return {"page": 1, "per_page": total, "total": total, "total_pages": 1}
    total_pages = max(1, -(-total // pagination.per_page))
    return {
        "page": pagination.page,
        "per_page": pagination.per_page,
        "total": total,
        "total_pages": total_pages,
    }


def window_for(pagination: Pagination) -> tuple[int | None, int]:
    """Return `(limit, offset)`. A None limit means "return the whole list"."""
    if pagination.per_page is None:
        return None, 0
    return pagination.per_page, (pagination.page - 1) * pagination.per_page
