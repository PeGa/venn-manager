"""Domain errors carrying contract error codes.

Deliberately free of Flask, HTTP and JSON: the core raises these, and
`app.middleware.errors` is the only place that knows which code maps to which
status (API_SURFACE.md § Design principle — hexagonal).
"""

from __future__ import annotations

UNAUTHORIZED = "UNAUTHORIZED"
FORBIDDEN = "FORBIDDEN"
PASSWORD_CHANGE_REQUIRED = "PASSWORD_CHANGE_REQUIRED"
NOT_FOUND = "NOT_FOUND"
CONFLICT = "CONFLICT"
GONE = "GONE"
VALIDATION_ERROR = "VALIDATION_ERROR"
INTERNAL_ERROR = "INTERNAL_ERROR"

#: Exact message required by API_SURFACE.md for every 410 response.
GONE_MESSAGE = "Record not available anymore."


class DomainError(Exception):
    """A business-rule violation identified by a contract error code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def validation_error(message: str) -> DomainError:
    """Build a `422 VALIDATION_ERROR`.

    *message* must be a static string: AGENTS.md § XSS Prevention forbids
    reflecting unvalidated request input back to the client.
    """
    return DomainError(VALIDATION_ERROR, message)


def not_found(message: str = "Resource not found") -> DomainError:
    """Build a `404 NOT_FOUND`."""
    return DomainError(NOT_FOUND, message)


def conflict(message: str) -> DomainError:
    """Build a `409 CONFLICT`."""
    return DomainError(CONFLICT, message)


def forbidden(message: str) -> DomainError:
    """Build a `403 FORBIDDEN`."""
    return DomainError(FORBIDDEN, message)


def unauthorized(message: str = "No active session") -> DomainError:
    """Build a `401 UNAUTHORIZED`."""
    return DomainError(UNAUTHORIZED, message)


def gone() -> DomainError:
    """Build the `410 GONE` returned for every soft-deleted target."""
    return DomainError(GONE, GONE_MESSAGE)


def password_change_required() -> DomainError:
    """Build the `403 PASSWORD_CHANGE_REQUIRED` gate response."""
    return DomainError(
        PASSWORD_CHANGE_REQUIRED, "Password change required before continuing"
    )
