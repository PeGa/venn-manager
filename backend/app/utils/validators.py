"""Input validation utilities.

Provides validation for dates, amounts, enums, strings, and currency symbols.
All validators raise ValueError with a descriptive message on failure.
"""

import re
from datetime import datetime
from decimal import Decimal, InvalidOperation

import grapheme


def validate_date(date_str: str) -> str:
    """Validate and return a date string in YYYY-MM-DD format.

    Args:
        date_str: Date string to validate.

    Returns:
        The validated date string.

    Raises:
        ValueError: If format is invalid or date doesn't exist.
    """
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise ValueError("Invalid date format. Expected YYYY-MM-DD")
    return date_str


def validate_month(month_str: str) -> str:
    """Validate and return a month string in YYYY-MM format.

    Args:
        month_str: Month string to validate.

    Returns:
        The validated month string.

    Raises:
        ValueError: If format is invalid.
    """
    if not re.match(r"^\d{4}-\d{2}$", month_str):
        raise ValueError("Invalid month format. Expected YYYY-MM")
    year, month = int(month_str[:4]), int(month_str[5:7])
    if month < 1 or month > 12:
        raise ValueError("Invalid month value. Must be 01-12")
    return month_str


def validate_amount(amount: object) -> Decimal:
    """Validate and return an amount as Decimal with at most 2 decimal places.

    Args:
        amount: The amount value (number or string).

    Returns:
        Decimal representation.

    Raises:
        ValueError: If not a valid decimal or has more than 2 decimal places.
    """
    try:
        d = Decimal(str(amount))
    except (InvalidOperation, ValueError):
        raise ValueError("Invalid amount. Must be a number")
    if d.as_tuple().exponent < -2:
        raise ValueError("Amount must have at most 2 decimal places")
    return d


def validate_string(value: str, max_length: int, field_name: str) -> str:
    """Validate a string: strip whitespace, check max length.

    Args:
        value: The string to validate.
        max_length: Maximum allowed length.
        field_name: Name of the field for error messages.

    Returns:
        Stripped and validated string.

    Raises:
        ValueError: If empty after stripping or exceeds max length.
    """
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")
    stripped = value.strip()
    if not stripped:
        raise ValueError(f"{field_name} is required")
    if len(stripped) > max_length:
        raise ValueError(f"{field_name} must be at most {max_length} characters")
    return stripped


def validate_flow(flow: str) -> str:
    """Validate flow value is 'IN' or 'OUT'.

    Args:
        flow: The flow value to validate.

    Returns:
        The validated flow string.

    Raises:
        ValueError: If not 'IN' or 'OUT'.
    """
    if flow not in ("IN", "OUT"):
        raise ValueError("Flow must be 'IN' or 'OUT'")
    return flow


def validate_theme(theme: str) -> str:
    """Validate theme value is 'light', 'dark', or 'system'.

    Args:
        theme: The theme value to validate.

    Returns:
        The validated theme string.

    Raises:
        ValueError: If not a valid theme value.
    """
    if theme not in ("light", "dark", "system"):
        raise ValueError("Theme must be 'light', 'dark', or 'system'")
    return theme


def validate_currency(currency: str) -> str:
    """Validate currency is exactly one grapheme cluster.

    Uses the grapheme library to correctly handle multi-codepoint
    characters like emoji.

    Args:
        currency: The currency string to validate.

    Returns:
        The validated currency string.

    Raises:
        ValueError: If not exactly one grapheme cluster.
    """
    if not isinstance(currency, str):
        raise ValueError("Currency must be a string")
    count = grapheme.length(currency)
    if count != 1:
        raise ValueError("Currency must be exactly one grapheme cluster")
    return currency
