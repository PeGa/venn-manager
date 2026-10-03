"""The current period (BACKEND.md § 3)."""

from datetime import UTC, date, datetime

from app.domain.period import current_period


def test_current_period_mid_month_spans_the_calendar_month() -> None:
    period = current_period("UTC", datetime(2026, 9, 28, 10, tzinfo=UTC))
    assert period.month == "2026-09"
    assert period.start == date(2026, 9, 1)
    assert period.end == date(2026, 9, 30)
    assert period.today == date(2026, 9, 28)
    assert period.days_in_month == 30


def test_current_period_uses_the_household_timezone() -> None:
    late_utc = datetime(2026, 9, 30, 23, 30, tzinfo=UTC)
    assert current_period("UTC", late_utc).month == "2026-09"
    assert current_period("Europe/Madrid", late_utc).month == "2026-10"


def test_current_period_in_february_of_a_leap_year_has_29_days() -> None:
    period = current_period("UTC", datetime(2028, 2, 10, tzinfo=UTC))
    assert period.end == date(2028, 2, 29)


def test_period_contains_only_its_own_days() -> None:
    period = current_period("UTC", datetime(2026, 9, 28, tzinfo=UTC))
    assert period.contains(date(2026, 9, 1))
    assert period.contains(date(2026, 9, 30))
    assert not period.contains(date(2026, 8, 31))
    assert not period.contains(date(2026, 10, 1))
