"""Transactions of the current period (BACKEND.md § 7)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

from app.application.activity import record
from app.application.auth import Auth
from app.application.common import commit_mutation, period
from app.domain.activity import NO_TARGET, Target
from app.domain.entities import Budget, Member, Transaction
from app.domain.errors import gone, not_found, validation
from app.domain.period import Period
from app.domain.transactions import (
    is_archived,
    require_amount,
    require_in_period,
    require_writable,
)
from app.ports import Context


@dataclass(frozen=True)
class TransactionView:
    """A transaction as the API shows it (API_SURFACE.md § 1.5)."""

    id: UUID
    budget_id: UUID
    category: str
    category_deleted: bool
    amount: int
    member_id: UUID
    date: date
    created_at: datetime
    updated_at: datetime
    archived: bool


@dataclass(frozen=True)
class NewTransaction:
    """A transaction to log. `date` and `member_id` have defaults."""

    budget_id: UUID
    amount: int
    date: date | None = None
    member_id: UUID | None = None


@dataclass(frozen=True)
class TransactionChanges:
    """Fields to change. `None` means "leave as is"."""

    budget_id: UUID | None = None
    amount: int | None = None
    date: date | None = None
    member_id: UUID | None = None


def view(transaction: Transaction, budget: Budget, current: Period) -> TransactionView:
    """Shape *transaction* with its budget's current name and state."""
    return TransactionView(
        id=transaction.id,
        budget_id=budget.id,
        category=budget.name,
        category_deleted=budget.is_deleted,
        amount=transaction.amount,
        member_id=transaction.member_id,
        date=transaction.date,
        created_at=transaction.created_at,
        updated_at=transaction.updated_at,
        archived=is_archived(transaction.date, current),
    )


def list_current(
    ctx: Context, offset: int, limit: int
) -> tuple[list[TransactionView], int]:
    """One page of this period's transactions, and how many there are."""
    current = period(ctx)
    rows = ctx.uow.transactions.page(current.start, current.end, offset, limit)
    total = ctx.uow.transactions.count(current.start, current.end)
    return [view(t, b, current) for t, b in rows], total


def _budget(ctx: Context, budget_id: UUID) -> Budget:
    budget = ctx.uow.budgets.get(budget_id)
    if budget is None:
        raise validation("Unknown budget", "budgetId")
    if budget.is_deleted:
        raise gone()
    return budget


def _member(ctx: Context, member_id: UUID) -> Member:
    member = ctx.uow.members.get(member_id)
    if member is None or member.is_removed:
        raise validation("Unknown member", "memberId")
    return member


def _writable(
    ctx: Context, transaction_id: UUID, current: Period
) -> tuple[Transaction, Budget]:
    found = ctx.uow.transactions.get(transaction_id)
    if found is None:
        raise not_found()
    transaction, budget = found
    if transaction.is_deleted:
        raise gone()
    require_writable(transaction, budget, current)
    return transaction, budget


def _log(
    ctx: Context, auth: Auth, transaction: Transaction, budget: Budget, action: str
) -> None:
    params = {"category": budget.name, "amount": transaction.amount}
    record(ctx, auth.member.id, action, params, Target("transaction", transaction.id))


def create(ctx: Context, auth: Auth, new: NewTransaction) -> TransactionView:
    """Log a signed amount against a budget, dated inside this period."""
    current = period(ctx)
    require_amount(new.amount)
    day = new.date or current.today
    require_in_period(day, current)
    budget = _budget(ctx, new.budget_id)
    member = _member(ctx, new.member_id) if new.member_id else auth.member
    now = ctx.clock.now()
    transaction = Transaction(
        budget_id=budget.id,
        amount=new.amount,
        member_id=member.id,
        date=day,
        created_by=auth.member.id,
        created_at=now,
        updated_at=now,
    )
    ctx.uow.transactions.add(transaction)
    _log(ctx, auth, transaction, budget, "tx.create")
    commit_mutation(ctx)
    return view(transaction, budget, current)


def update(
    ctx: Context, auth: Auth, transaction_id: UUID, changes: TransactionChanges
) -> TransactionView:
    """Edit a writable transaction. Same rules as creating one."""
    current = period(ctx)
    transaction, budget = _writable(ctx, transaction_id, current)
    if changes.amount is not None:
        require_amount(changes.amount)
        transaction.amount = changes.amount
    if changes.date is not None:
        require_in_period(changes.date, current)
        transaction.date = changes.date
    if changes.budget_id is not None:
        budget = _budget(ctx, changes.budget_id)
        transaction.budget_id = budget.id
    if changes.member_id is not None:
        transaction.member_id = _member(ctx, changes.member_id).id
    transaction.updated_at = ctx.clock.now()
    _log(ctx, auth, transaction, budget, "tx.update")
    commit_mutation(ctx)
    return view(transaction, budget, current)


def delete(ctx: Context, auth: Auth, transaction_id: UUID) -> None:
    """Soft-delete a writable transaction."""
    transaction, budget = _writable(ctx, transaction_id, period(ctx))
    transaction.is_deleted = True
    _log(ctx, auth, transaction, budget, "tx.delete")
    commit_mutation(ctx)


def bulk_delete(
    ctx: Context, auth: Auth, ids: list[UUID]
) -> tuple[list[UUID], list[UUID]]:
    """All-or-nothing for the ids found. Returns (deleted, not found)."""
    current = period(ctx)
    found: list[Transaction] = []
    missing: list[UUID] = []
    for transaction_id in dict.fromkeys(ids):
        row = ctx.uow.transactions.get(transaction_id)
        if row is None or row[0].is_deleted:
            missing.append(transaction_id)
        else:
            require_writable(row[0], row[1], current)
            found.append(row[0])
    if not found:
        return [], missing
    for transaction in found:
        transaction.is_deleted = True
    record(ctx, auth.member.id, "tx.bulkDelete", {"count": len(found)}, NO_TARGET)
    commit_mutation(ctx)
    return [t.id for t in found], missing
