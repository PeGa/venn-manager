"""HTTP request adapters: body and query parsing.

Everything here touches `flask.request`. Domain rules stay in `app.utils` and
`app.services`, so this module is the only place that knows a body came in over
HTTP (API_SURFACE.md § Design principle).
"""

from __future__ import annotations

from datetime import date
from typing import Any

from flask import Request, current_app

from app.config import Clock
from app.services.errors import validation_error
from app.utils.pagination import ALL, ALLOWED_PAGE_SIZES, DEFAULT_PAGE_SIZE, Pagination


def today() -> date:
    """Return "today" through the injected clock.

    Production wires `date.today`; tests inject a fixed date so month-sensitive
    behaviour stays deterministic.
    """
    clock: Clock = current_app.config["CLOCK"]
    return clock()


def json_body(request: Request) -> dict[str, Any]:
    """Return the request body as a mapping, or raise `422 VALIDATION_ERROR`.

    `silent=True` turns malformed JSON into None, which is reported as a
    validation failure rather than werkzeug's generic 400.
    """
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise validation_error("Request body must be a JSON object")
    return payload


def require_query(request: Request, name: str) -> str:
    """Return a required, non-empty query parameter."""
    value = request.args.get(name)
    if value is None or not value.strip():
        raise validation_error(f"Query parameter '{name}' is required")
    return value.strip()


def optional_query(request: Request, name: str) -> str | None:
    """Return a query parameter, or None when absent or blank."""
    value = request.args.get(name)
    if value is None or not value.strip():
        return None
    return value.strip()


def boolean_query(request: Request, name: str, *, default: bool = False) -> bool:
    """Return a boolean query parameter.

    Only the explicit spellings `true`/`1` and `false`/`0` are accepted;
    anything else is a validation error rather than a silent default.
    """
    raw = optional_query(request, name)
    if raw is None:
        return default
    lowered = raw.lower()
    if lowered in ("true", "1"):
        return True
    if lowered in ("false", "0"):
        return False
    raise validation_error(f"Query parameter '{name}' must be a boolean")


def _positive_int(raw: str, name: str, allowed: tuple[int, ...] | None = None) -> int:
    """Parse a strictly positive integer query parameter."""
    if not (raw.isascii() and raw.isdigit()):
        raise validation_error(f"Query parameter '{name}' must be a positive integer")
    value = int(raw)
    if value < 1:
        raise validation_error(f"Query parameter '{name}' must be a positive integer")
    if allowed is not None and value not in allowed:
        allowed_list = ", ".join(str(item) for item in allowed)
        raise validation_error(
            f"Query parameter '{name}' must be one of: {allowed_list}, {ALL}"
        )
    return value


def parse_pagination(request: Request) -> Pagination:
    """Resolve `page` and `q` into a :class:`Pagination`.

    `q=all` returns every row and reports `page` as 1, since paging a complete
    list is meaningless.
    """
    raw_page = optional_query(request, "page") or "1"
    raw_size = optional_query(request, "q") or str(DEFAULT_PAGE_SIZE)
    if raw_size == ALL:
        return Pagination(page=1, per_page=None)
    page = _positive_int(raw_page, "page")
    per_page = _positive_int(raw_size, "q", ALLOWED_PAGE_SIZES)
    return Pagination(page=page, per_page=per_page)
