"""Error body and handlers (API_SURFACE.md § 11).

Every error leaves the API as `{ code, message, field? }`. Messages are fixed
strings: they never echo request input, stack traces, SQL or paths.
"""

from __future__ import annotations

import logging
from typing import cast

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("venn_manager")


class AppError(Exception):
    """A domain or request error with its HTTP status and contract code."""

    def __init__(
        self, status: int, code: str, message: str, field: str | None = None
    ) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.field = field


def validation(message: str, field: str | None = None) -> AppError:
    """`400 VALIDATION`."""
    return AppError(400, "VALIDATION", message, field)


def not_found() -> AppError:
    """`404 NOT_FOUND`."""
    return AppError(404, "NOT_FOUND", "Not found")


def gone() -> AppError:
    """`410 GONE` for soft-deleted targets (BACKEND.md § 12)."""
    return AppError(410, "GONE", "Record not available anymore.")


def error_response(
    status: int, code: str, message: str, field: str | None = None
) -> JSONResponse:
    """Build the contract error body."""
    body: dict[str, str] = {"code": code, "message": message}
    if field is not None:
        body["field"] = field
    return JSONResponse(status_code=status, content=body)


def _field_from_location(location: tuple[int | str, ...]) -> str | None:
    names = [part for part in location[1:] if isinstance(part, str)]
    return names[-1] if names else None


async def _handle_app_error(_request: Request, exc: Exception) -> JSONResponse:
    error = cast(AppError, exc)
    return error_response(error.status, error.code, error.message, error.field)


async def _handle_validation(_request: Request, exc: Exception) -> JSONResponse:
    errors = cast(RequestValidationError, exc).errors()
    field = _field_from_location(tuple(errors[0]["loc"])) if errors else None
    message = f"Invalid {field}" if field else "Invalid request"
    return error_response(400, "VALIDATION", message, field)


async def _handle_http(_request: Request, exc: Exception) -> JSONResponse:
    status = cast(StarletteHTTPException, exc).status_code
    if status in (404, 405):
        return error_response(404, "NOT_FOUND", "Not found")
    if status == 400:
        return error_response(400, "VALIDATION", "Invalid request")
    return error_response(status, "INTERNAL", "Unexpected error")


async def _handle_unexpected(_request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error", exc_info=exc)
    return error_response(500, "INTERNAL", "Unexpected error")


def install_error_handlers(app: FastAPI) -> None:
    """Route every exception through the contract error body."""
    app.add_exception_handler(AppError, _handle_app_error)
    app.add_exception_handler(RequestValidationError, _handle_validation)
    app.add_exception_handler(StarletteHTTPException, _handle_http)
    app.add_exception_handler(Exception, _handle_unexpected)
