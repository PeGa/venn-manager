"""Budget rules and per-budget figures (BACKEND.md § 4.2, § 6)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

BUDGET_NAME_MAX = 60
REPEATS = ("once", "weekly", "biweekly", "monthly")


@dataclass(frozen=True)
class Schedule:
    """When a budget is due. `anchor` is the first (or only) due date."""

    repeat: str
    anchor: date


@dataclass(frozen=True)
class BudgetFigures:
    """The derived numbers for one budget in the current period."""

    actual: int
    projected: int
    remaining: int
    over: bool
    over_by: int
    progress_pct: float


def projected(amount: int, actual: int) -> int:
    """The plan, unless what happened went past it in the same direction."""
    if amount > 0:
        return max(amount, actual)
    if amount < 0:
        return min(amount, actual)
    return actual


def figures(amount: int, actual: int) -> BudgetFigures:
    """BACKEND.md § 4.2, for a signed budget *amount* and signed *actual*."""
    plan = projected(amount, actual)
    over = plan != amount if amount != 0 else actual != 0
    same_sign = amount * actual > 0
    progress = min(100.0, abs(actual) / abs(amount) * 100) if same_sign else 0.0
    return BudgetFigures(
        actual=actual,
        projected=plan,
        remaining=plan - actual,
        over=over,
        over_by=abs(actual - amount) if over else 0,
        progress_pct=progress,
    )
