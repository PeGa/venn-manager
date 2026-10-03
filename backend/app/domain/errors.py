"""Domain errors. They carry a contract code; adapters decide the transport status.

Codes and meanings: API_SURFACE.md § 11. Messages are fixed text and never
echo input.
"""

from __future__ import annotations


class DomainError(Exception):
    """A rule was broken. `code` is the contract error code."""

    def __init__(self, code: str, message: str, field: str | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.field = field


def validation(message: str, field: str | None = None) -> DomainError:
    """`VALIDATION`."""
    return DomainError("VALIDATION", message, field)


def not_found() -> DomainError:
    """`NOT_FOUND`."""
    return DomainError("NOT_FOUND", "Not found")


def gone() -> DomainError:
    """`GONE`: the target was soft-deleted (BACKEND.md § 12)."""
    return DomainError("GONE", "Record not available anymore.")
