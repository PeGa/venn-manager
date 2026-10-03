"""Tests for the pure month helpers (BACKEND.md § 1.4, § 3)."""

from __future__ import annotations

from datetime import date, datetime, timezone

from app.utils.dates import (
    is_before,
    month_bounds,
    month_key,
    next_month,
    previous_month,
    utc_now,
)


class TestMonthKey:
    def test_renders_zero_padded(self) -> None:
        assert month_key(date(2025, 3, 7)) == "2025-03"

    def test_renders_december(self) -> None:
        assert month_key(date(2025, 12, 31)) == "2025-12"


class TestMonthBounds:
    def test_thirty_one_day_month(self) -> None:
        assert month_bounds("2025-07") == (date(2025, 7, 1), date(2025, 7, 31))

    def test_leap_february(self) -> None:
        assert month_bounds("2024-02") == (date(2024, 2, 1), date(2024, 2, 29))

    def test_non_leap_february(self) -> None:
        assert month_bounds("2025-02") == (date(2025, 2, 1), date(2025, 2, 28))


class TestMonthArithmetic:
    def test_previous_month_within_a_year(self) -> None:
        assert previous_month("2025-07") == "2025-06"

    def test_previous_month_wraps_to_december(self) -> None:
        assert previous_month("2025-01") == "2024-12"

    def test_next_month_within_a_year(self) -> None:
        assert next_month("2025-07") == "2025-08"

    def test_next_month_wraps_to_january(self) -> None:
        assert next_month("2025-12") == "2026-01"


class TestIsBefore:
    def test_earlier_month(self) -> None:
        assert is_before("2025-06", "2025-07") is True

    def test_later_month(self) -> None:
        assert is_before("2025-08", "2025-07") is False

    def test_same_month(self) -> None:
        assert is_before("2025-07", "2025-07") is False

    def test_crosses_a_year_boundary(self) -> None:
        assert is_before("2024-12", "2025-01") is True


class TestUtcNow:
    def test_is_naive(self) -> None:
        assert utc_now().tzinfo is None

    def test_is_close_to_the_system_clock(self) -> None:
        reference = datetime.now(timezone.utc).replace(tzinfo=None)

        assert abs((reference - utc_now()).total_seconds()) < 5
