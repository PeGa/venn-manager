"""The Balance screen (BACKEND.md § 4.5)."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.application.common import period
from app.ports import Context


@dataclass(frozen=True)
class MemberIncome:
    """What one member brought in."""

    member_id: UUID
    month_in: int
    all_time_in: int


@dataclass(frozen=True)
class BalanceView:
    """The household balance and this period's flows."""

    balance: int
    month_in: int
    month_out: int
    members: list[MemberIncome] | None


def balance(ctx: Context) -> BalanceView:
    """`balance = startCash + transactionsNet` (BACKEND.md § 4.5)."""
    current = period(ctx)
    household = ctx.uow.household.get()
    txs = ctx.uow.transactions
    month_in, month_out = txs.flows(current.start, current.end)
    start_cash = household.opening_balance + txs.net_before(current.start)
    members = None
    if household.show_member_income:
        this_month = txs.income_by_member(current.start, current.end)
        all_time = txs.income_by_member()
        members = [
            MemberIncome(member_id, this_month.get(member_id, 0), total)
            for member_id, total in sorted(all_time.items(), key=lambda kv: -kv[1])
        ]
    return BalanceView(start_cash + month_in - month_out, month_in, month_out, members)
