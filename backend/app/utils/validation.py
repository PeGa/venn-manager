"""Request-shape validation.

Pure functions over plain Python values — no Flask, no SQLAlchemy, so the same
rules are reusable from the domain layer. Every message is static:
AGENTS.md § XSS Prevention forbids reflecting unvalidated request input back
to the client.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

import grapheme

from app.services.errors import validation_error

MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128

#: AGENTS.md § API Abuse Prevention: bulk endpoints cap the ids per request.
MAX_BULK_IDS = 100

#: DECIMAL(10,2) per the API_SURFACE.md reference schema.
MAX_AMOUNT = Decimal("99999999.99")
MAX_DECIMAL_PLACES = 2

DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
MONTH_PATTERN = re.compile(r"^\d{4}-\d{2}$")


def _field_message(field: str, problem: str) -> str:
    """Build a static message naming only the field, never the submitted value."""
    return f"Field '{field}' {problem}"


def validate_text(
    value: Any,
    *,
    field: str,
    max_length: int,
    min_length: int = 1,
    strip: bool = True,
) -> str:
    """Validate one string value against a field's length rules.

    *strip* is False for passwords: a trailing space is part of the secret, so
    trimming it would silently change the credential.
    """
    if not isinstance(value, str):
        raise validation_error(_field_message(field, "must be a string"))
    cleaned = value.strip() if strip else value
    if len(cleaned) < min_length:
        raise validation_error(
            _field_message(field, f"must be at least {min_length} characters")
        )
    if len(cleaned) > max_length:
        raise validation_error(
            _field_message(field, f"must be at most {max_length} characters")
        )
    return cleaned


def require_string(
    payload: Mapping[str, Any],
    field: str,
    *,
    max_length: int,
    min_length: int = 1,
    strip: bool = True,
) -> str:
    """Return a required string field from *payload*, trimmed and length-checked."""
    value = payload.get(field)
    if not isinstance(value, str):
        raise validation_error(
            _field_message(field, "is required and must be a string")
        )
    return validate_text(
        value, field=field, max_length=max_length, min_length=min_length, strip=strip
    )


def optional_string(
    payload: Mapping[str, Any],
    field: str,
    *,
    max_length: int,
    min_length: int = 1,
    strip: bool = True,
) -> str | None:
    """Return an optional string field, or None when absent or null."""
    if payload.get(field) is None:
        return None
    return require_string(
        payload, field, max_length=max_length, min_length=min_length, strip=strip
    )


def validate_choice(value: Any, field: str, choices: Sequence[str]) -> str:
    """Return *value* unchanged when it is one of *choices*."""
    if not isinstance(value, str) or value not in choices:
        allowed = ", ".join(choices)
        raise validation_error(_field_message(field, f"must be one of: {allowed}"))
    return value


def require_choice(
    payload: Mapping[str, Any], field: str, choices: Sequence[str]
) -> str:
    """Return a required field from *payload* that must equal one of *choices*."""
    return validate_choice(payload.get(field), field, choices)


def validate_currency(value: Any) -> str:
    """Validate the currency symbol as exactly one grapheme cluster.

    AGENTS.md § Input Validation forbids `len()` here: a multi-codepoint emoji
    such as a ZWJ family is a single symbol to the user but 8 code points to
    Python. FRONTEND.md § 5.1.3 explicitly allows that.
    """
    if not isinstance(value, str):
        raise validation_error(_field_message("currency", "must be a string"))
    cleaned = value.strip()
    if grapheme.length(cleaned) != 1:
        raise validation_error(
            _field_message("currency", "must be exactly one character")
        )
    return cleaned


def validate_password(value: str) -> str:
    """Enforce the password length policy and return the value unchanged.

    The contracts require "too short" to be rejected but never fix a number;
    8 characters is the documented floor in docs/BACKEND.md § Contract gaps.
    """
    if len(value) < MIN_PASSWORD_LENGTH:
        raise validation_error(
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters"
        )
    if len(value) > MAX_PASSWORD_LENGTH:
        raise validation_error(
            f"Password must be at most {MAX_PASSWORD_LENGTH} characters"
        )
    return value


def optional_bool(
    payload: Mapping[str, Any], field: str, *, default: bool = False
) -> bool:
    """Return an optional boolean field. JSON `true`/`false` only.

    Strings such as `"yes"` are rejected: AGENTS.md § API Abuse Prevention
    requires type validation, not coercion.
    """
    if field not in payload or payload[field] is None:
        return default
    value = payload[field]
    if not isinstance(value, bool):
        raise validation_error(_field_message(field, "must be a boolean"))
    return value


def nullable_bool(payload: Mapping[str, Any], field: str) -> bool | None:
    """Return an optional boolean field, or None when it was not submitted.

    Used by PATCH handlers, where "absent" means "leave unchanged" and must stay
    distinguishable from an explicit `false`.
    """
    if field not in payload or payload[field] is None:
        return None
    value = payload[field]
    if not isinstance(value, bool):
        raise validation_error(_field_message(field, "must be a boolean"))
    return value


def parse_amount(
    value: Any, *, field: str = "amount", nullable: bool = False
) -> Decimal | None:
    """Parse a monetary value into a `Decimal` with at most two places.

    Numbers and numeric strings are both accepted, because a browser number
    input hands the frontend a string. Booleans are rejected explicitly: Python
    treats `True` as `1`, which would silently record a 1.00 transaction.
    Converting through `str()` keeps `0.1 + 0.2 = 0.3` true
    (FRONTEND.md § Database assumptions).
    """
    if value is None:
        if nullable:
            return None
        raise validation_error(_field_message(field, "is required"))
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise validation_error(_field_message(field, "must be a number"))
    try:
        amount = Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        raise validation_error(_field_message(field, "must be a number")) from None
    if not amount.is_finite():
        raise validation_error(_field_message(field, "must be a finite number"))
    exponent = amount.as_tuple().exponent
    if isinstance(exponent, int) and exponent < -MAX_DECIMAL_PLACES:
        raise validation_error(
            _field_message(
                field, f"must have at most {MAX_DECIMAL_PLACES} decimal places"
            )
        )
    if abs(amount) > MAX_AMOUNT:
        raise validation_error(_field_message(field, "is out of range"))
    return amount


def parse_date(value: Any, *, field: str = "date") -> date:
    """Parse a strict `YYYY-MM-DD` date.

    The regex runs first because `strptime` accepts unpadded components such as
    `2025-7-5`, which the contract's format forbids.
    """
    if not isinstance(value, str) or not DATE_PATTERN.match(value):
        raise validation_error(_field_message(field, "must be a YYYY-MM-DD date"))
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        raise validation_error(
            _field_message(field, "must be a real calendar date")
        ) from None


def parse_month(value: Any, *, field: str = "month") -> str:
    """Validate a `YYYY-MM` month identifier and return it unchanged."""
    if not isinstance(value, str) or not MONTH_PATTERN.match(value):
        raise validation_error(_field_message(field, "must be a YYYY-MM month"))
    if not 1 <= int(value[5:7]) <= 12:
        raise validation_error(_field_message(field, "must be a YYYY-MM month"))
    return value


def parse_int(value: Any, *, field: str) -> int:
    """Parse a strictly positive integer identifier from a request body."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise validation_error(_field_message(field, "must be an integer"))
    if value < 1:
        raise validation_error(_field_message(field, "must be a positive integer"))
    return value


def parse_id_list(raw: str | None, *, field: str = "ids") -> list[int]:
    """Parse a comma-separated id list for the bulk-delete endpoints.

    Duplicates collapse, so the 100-id cap in AGENTS.md § API Abuse Prevention
    applies to distinct ids. Messages never echo the submitted value.
    """
    if raw is None or not raw.strip():
        raise validation_error(f"Query parameter '{field}' is required")
    parsed: list[int] = []
    for part in raw.split(","):
        token = part.strip()
        if not (token.isascii() and token.isdigit()):
            raise validation_error(
                f"Query parameter '{field}' must be a comma-separated list of ids"
            )
        value = int(token)
        if value not in parsed:
            parsed.append(value)
    if not parsed:
        raise validation_error(f"Query parameter '{field}' must not be empty")
    if len(parsed) > MAX_BULK_IDS:
        raise validation_error(
            f"Query parameter '{field}' accepts at most {MAX_BULK_IDS} ids"
        )
    return parsed
