"""Error handling: every failure leaves through the response envelope.

This is the only module that knows which contract error code maps to which
HTTP status, keeping `app.services` free of HTTP concepts
(API_SURFACE.md § Design principle).
"""

from __future__ import annotations

import logging

from flask import Flask, Response, jsonify
from werkzeug.exceptions import HTTPException

from app.middleware.responses import error_body
from app.services.errors import (
    CONFLICT,
    FORBIDDEN,
    GONE,
    GONE_MESSAGE,
    INTERNAL_ERROR,
    NOT_FOUND,
    PASSWORD_CHANGE_REQUIRED,
    UNAUTHORIZED,
    VALIDATION_ERROR,
    DomainError,
)

logger = logging.getLogger(__name__)

STATUS_BY_CODE: dict[str, int] = {
    UNAUTHORIZED: 401,
    FORBIDDEN: 403,
    PASSWORD_CHANGE_REQUIRED: 403,
    NOT_FOUND: 404,
    CONFLICT: 409,
    GONE: 410,
    VALIDATION_ERROR: 422,
    INTERNAL_ERROR: 500,
}

#: API_SURFACE.md documents a closed set of status codes and no 405/400/415,
#: so those transport-level failures are folded into the documented set:
#: a bad or unsupported request is a validation problem, and an unsupported
#: method on a known path is reported as not found.
_HTTP_STATUS_FALLBACK: dict[int, tuple[str, int]] = {
    400: (VALIDATION_ERROR, 422),
    401: (UNAUTHORIZED, 401),
    403: (FORBIDDEN, 403),
    404: (NOT_FOUND, 404),
    405: (NOT_FOUND, 404),
    409: (CONFLICT, 409),
    410: (GONE, 410),
    415: (VALIDATION_ERROR, 422),
    422: (VALIDATION_ERROR, 422),
}

INTERNAL_ERROR_MESSAGE = "Internal server error"


def _render(code: str, message: str, status: int) -> tuple[Response, int]:
    return jsonify(error_body(code, message)), status


def register_error_handlers(app: Flask) -> None:
    """Attach the envelope-returning handlers to *app*."""

    @app.errorhandler(DomainError)
    def handle_domain_error(error: DomainError) -> tuple[Response, int]:
        """Map a business-rule violation onto its contract status."""
        status = STATUS_BY_CODE.get(error.code, 500)
        if status >= 500:
            logger.error("Unhandled domain error code %s", error.code)
        else:
            logger.info("Rejected request: %s", error.code)
        return _render(error.code, error.message, status)

    @app.errorhandler(HTTPException)
    def handle_http_exception(error: HTTPException) -> tuple[Response, int]:
        """Fold routing/transport errors into the documented status set."""
        code, status = _HTTP_STATUS_FALLBACK.get(
            error.code or 500,
            (
                (VALIDATION_ERROR, 422)
                if (error.code or 0) < 500
                else (INTERNAL_ERROR, 500)
            ),
        )
        message = GONE_MESSAGE if code == GONE else _message_for(code)
        logger.info("Transport error %s reported as %s", error.code, code)
        return _render(code, message, status)

    @app.errorhandler(Exception)
    def handle_unexpected(error: Exception) -> tuple[Response, int]:
        """Log the real cause, return a sanitised body.

        AGENTS.md § Error Handling Patterns: never expose stack traces, SQL or
        internal paths to the client.
        """
        logger.exception("Unhandled exception", exc_info=error)
        return _render(INTERNAL_ERROR, INTERNAL_ERROR_MESSAGE, 500)


def _message_for(code: str) -> str:
    """Return the standard human-readable message for a contract code."""
    if code == VALIDATION_ERROR:
        return "Request validation failed"
    if code == INTERNAL_ERROR:
        return INTERNAL_ERROR_MESSAGE
    if code == UNAUTHORIZED:
        return "No active session"
    if code == FORBIDDEN:
        return "Not permitted"
    return "Resource not found"
