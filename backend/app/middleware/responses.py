"""Response envelope helpers (API_SURFACE.md § Response Envelope)."""

from __future__ import annotations

from typing import Any

from flask import Response, jsonify


def envelope(
    data: Any = None,
    *,
    error: dict[str, str] | None = None,
    meta: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Build the three-key body every endpoint returns, success or failure."""
    return {"data": data, "error": error, "meta": meta}


def respond(
    data: Any = None, *, meta: dict[str, int] | None = None, status: int = 200
) -> tuple[Response, int]:
    """Render a success response. `error` is always null here."""
    return jsonify(envelope(data, meta=meta)), status


def error_body(code: str, message: str) -> dict[str, Any]:
    """Render an error response body. `data` is always null here."""
    return envelope(error={"code": code, "message": message})
