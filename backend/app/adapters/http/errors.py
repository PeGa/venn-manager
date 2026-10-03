"""Error body and status mapping (API_SURFACE.md § 11).

Every error leaves as `{ code, message, field? }`. Domain errors carry the code;
this module alone decides the HTTP status.
"""

from __future__ import annotations

import logging
from typing import cast

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.domain.errors import DomainError

logger = logging.getLogger("venn_manager")

STATUS_BY_CODE = {
    "VALIDATION": 400,
    "OUT_OF_PERIOD": 400,
    "UNAUTHORIZED": 401,
    "PASSWORD_CHANGE_REQUIRED": 403,
    "FORBIDDEN": 403,
    "NOT_FOUND": 404,
    "DUPLICATE_NAME": 409,
    "LAST_ADMIN": 409,
    "SELF_REMOVAL": 409,
    "READ_ONLY_HISTORY": 409,
    "CATEGORY_DELETED": 409,
    "GONE": 410,
}


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


async def _handle_domain(_request: Request, exc: Exception) -> JSONResponse:
    error = cast(DomainError, exc)
    status = STATUS_BY_CODE[error.code]
    return error_response(status, error.code, error.message, error.field)


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
    app.add_exception_handler(DomainError, _handle_domain)
    app.add_exception_handler(RequestValidationError, _handle_validation)
    app.add_exception_handler(StarletteHTTPException, _handle_http)
    app.add_exception_handler(Exception, _handle_unexpected)
