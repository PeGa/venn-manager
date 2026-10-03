"""History helpers (BACKEND.md § 4.6)."""

from datetime import date

import pytest

from app.domain.history import month_bounds, percent


@pytest.mark.parametrize(
    ("part", "total", "expected"),
    [
        (1, 3, 33),
        (1, 2, 50),
        (1, 8, 13),
        (5, 8, 63),
        (0, 10, 0),
        (7, 7, 100),
        (0, 0, 0),
    ],
)
def test_percent_rounds_half_up(part: int, total: int, expected: int) -> None:
    assert percent(part, total) == expected


def test_month_bounds_of_a_valid_key() -> None:
    assert month_bounds("2026-02") == (date(2026, 2, 1), date(2026, 2, 28))
    assert month_bounds("2028-02") == (date(2028, 2, 1), date(2028, 2, 29))


@pytest.mark.parametrize("key", ["2026-13", "2026-1", "26-01", "2026/01", "abcd-ef"])
def test_month_bounds_of_an_invalid_key_is_none(key: str) -> None:
    assert month_bounds(key) is None
