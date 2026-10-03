"""Coming up (BACKEND.md § 5)."""

from datetime import UTC, date, datetime
from uuid import uuid4

from app.domain.budgets import Schedule
from app.domain.period import Period, current_period
from app.domain.upcoming import Scheduled, occurrences, upcoming


def _period(day: date) -> Period:
    return current_period("UTC", datetime(day.year, day.month, day.day, tzinfo=UTC))


SEPT = _period(date(2026, 9, 18))


def _scheduled(
    repeat: str, anchor: date, amount: int = -1000, actual: int = 0, name: str = "Rent"
) -> Scheduled:
    return Scheduled(uuid4(), name, amount, actual, Schedule(repeat, anchor))


def test_occurrences_once_inside_and_outside_the_period() -> None:
    assert occurrences(Schedule("once", date(2026, 9, 20)), SEPT) == [date(2026, 9, 20)]
    assert occurrences(Schedule("once", date(2026, 10, 1)), SEPT) == []


def test_occurrences_weekly_from_an_earlier_anchor() -> None:
    days = occurrences(Schedule("weekly", date(2026, 8, 30)), SEPT)
    assert days == [date(2026, 9, d) for d in (6, 13, 20, 27)]


def test_occurrences_weekly_start_on_the_anchor() -> None:
    days = occurrences(Schedule("weekly", date(2026, 9, 16)), SEPT)
    assert days == [date(2026, 9, 16), date(2026, 9, 23), date(2026, 9, 30)]


def test_occurrences_biweekly_keep_the_14_day_rhythm() -> None:
    days = occurrences(Schedule("biweekly", date(2026, 8, 27)), SEPT)
    assert days == [date(2026, 9, 10), date(2026, 9, 24)]


def test_occurrences_monthly_from_the_anchor_month_on() -> None:
    assert occurrences(Schedule("monthly", date(2026, 7, 1)), SEPT) == [
        date(2026, 9, 1)
    ]
    assert occurrences(Schedule("monthly", date(2026, 10, 1)), SEPT) == []


def test_upcoming_with_monthly_anchor_on_31st_clamps_to_month_end() -> None:
    assert occurrences(Schedule("monthly", date(2026, 1, 31)), SEPT) == [
        date(2026, 9, 30)
    ]
    february = _period(date(2027, 2, 1))
    assert occurrences(Schedule("monthly", date(2026, 1, 31)), february) == [
        date(2027, 2, 28)
    ]


def test_upcoming_lists_the_next_occurrence() -> None:
    (item,) = upcoming([_scheduled("weekly", date(2026, 9, 6))], SEPT)
    assert item.due_date == date(2026, 9, 20)
    assert item.overdue is False
    assert item.soon is True


def test_upcoming_due_today_is_not_overdue() -> None:
    (item,) = upcoming([_scheduled("once", date(2026, 9, 18))], SEPT)
    assert (item.due_date, item.overdue, item.soon) == (date(2026, 9, 18), False, True)


def test_upcoming_far_away_is_not_soon() -> None:
    (item,) = upcoming([_scheduled("once", date(2026, 9, 22))], SEPT)
    assert item.soon is False


def test_upcoming_past_and_unpaid_is_overdue() -> None:
    (item,) = upcoming([_scheduled("monthly", date(2026, 1, 1))], SEPT)
    assert (item.due_date, item.overdue, item.soon) == (date(2026, 9, 1), True, True)


def test_upcoming_drops_done_budgets_in_both_directions() -> None:
    items = upcoming(
        [
            _scheduled("once", date(2026, 9, 25), amount=-8800, actual=-8800),
            _scheduled("once", date(2026, 9, 25), amount=224000, actual=230000),
        ],
        SEPT,
    )
    assert items == []


def test_upcoming_keeps_partially_paid_budgets() -> None:
    (item,) = upcoming([_scheduled("once", date(2026, 9, 25), -8800, -4000)], SEPT)
    assert (item.amount, item.actual) == (-8800, -4000)


def test_upcoming_skips_zero_budgets_and_periods_without_occurrences() -> None:
    items = upcoming(
        [
            _scheduled("once", date(2026, 9, 25), amount=0),
            _scheduled("once", date(2026, 10, 5)),
        ],
        SEPT,
    )
    assert items == []


def test_upcoming_sorts_by_date_then_name() -> None:
    items = upcoming(
        [
            _scheduled("once", date(2026, 9, 25), name="Internet"),
            _scheduled("once", date(2026, 9, 20), name="Water"),
            _scheduled("once", date(2026, 9, 25), name="Electric"),
        ],
        SEPT,
    )
    assert [i.name for i in items] == ["Water", "Electric", "Internet"]
