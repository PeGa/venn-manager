"""Record reads and writes (API_SURFACE.md § 4, BACKEND.md § 1.2 and § 5.1).

Transactions and budgets are separate tables with separate lifecycles; this
module is what presents them through the single `records` port.

The ghost rule lives here: a record's own `is_deleted` only ever reflects that
record, while visibility of records whose *concept* was deleted is derived per
query — hidden in the working month, kept and flagged in history.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Union, cast

from sqlalchemy import Select, func, select
from sqlalchemy.engine import RowMapping

from app.extensions import DbSession
from app.models import Budget, Concept, Transaction, User
from app.services.errors import gone, not_found, validation_error
from app.utils.dates import is_before, month_bounds
from app.utils.pagination import Pagination, meta_for, window_for

TRANSACTION = "transaction"
BUDGET = "budget"
RECORD_TYPES = (TRANSACTION, BUDGET)

NOT_FOUND_MESSAGE = "Record not found"
MISSING_CONCEPT_MESSAGE = "Concept does not exist or is no longer available"
AMOUNT_REQUIRED_MESSAGE = "Field 'amount' is required for a transaction"

RecordModel = Union[Transaction, Budget]


class _Unset:
    """Sentinel distinguishing "field absent" from "field explicitly null"."""


UNSET = _Unset()


@dataclass(frozen=True)
class RecordView:
    """One record with its concept and user resolved, ready to serialise."""

    id: int
    type: str
    date: date
    concept_id: int
    concept_name: str
    concept_flow: str
    concept_is_deleted: bool
    amount: Decimal | None
    user_id: int
    username: str
    user_is_deleted: bool
    created_at: datetime


def _model_for(kind: str) -> type[Transaction] | type[Budget]:
    return Transaction if kind == TRANSACTION else Budget


def list_records(
    session: DbSession,
    *,
    kind: str,
    pagination: Pagination,
    month: str | None = None,
    search: str | None = None,
    working_month: str | None = None,
) -> tuple[list[RecordView], dict[str, int]]:
    """Return one page of records plus the pagination meta block.

    Budgets are a standing list: every live budget of a live concept, whatever
    its date. Transactions are month-scoped, and the ghost rule depends on
    whether *month* is before the requester's working month.
    """
    history = (
        month is not None
        and working_month is not None
        and is_before(month, working_month)
    )
    statement = _filtered_query(kind, month=month, search=search, history=history)
    total = session.scalar(select(func.count()).select_from(statement.subquery()))
    limit, offset = window_for(pagination)
    model = _model_for(kind)
    rows = (
        session.execute(statement.order_by(model.id).limit(limit).offset(offset))
        .mappings()
        .all()
    )
    return [_to_view(kind, row) for row in rows], meta_for(int(total or 0), pagination)


def create_record(
    session: DbSession,
    *,
    kind: str,
    on: date,
    concept: Concept,
    amount: Decimal | None,
    user: User,
) -> RecordView:
    """Create a transaction or budget. Flushes; the caller commits.

    `flow` is never taken from the request: it is a property of the concept
    (BACKEND.md § 5.1).
    """
    record = _new_record(kind, on=on, concept=concept, amount=amount, user=user)
    session.add(record)
    session.flush()
    return RecordView(
        id=record.id,
        type=kind,
        date=record.date,
        concept_id=concept.id,
        concept_name=concept.name,
        concept_flow=concept.flow,
        concept_is_deleted=False,
        amount=record.amount,
        user_id=user.id,
        username=user.username,
        user_is_deleted=bool(user.is_deleted),
        created_at=record.created_at,
    )


def update_record(
    session: DbSession,
    *,
    kind: str,
    record_id: int,
    on: date | None = None,
    concept: Concept | None = None,
    amount: Decimal | None | _Unset = UNSET,
) -> RecordView:
    """Apply a partial update. Flushes; the caller commits.

    Raises 404 when no record of this type has that id, and 410 when the record
    or its concept is soft-deleted — the edit-vs-delete race outcome described
    in BACKEND.md § 1.3.
    """
    record, current_concept = load_writable_record(
        session, kind=kind, record_id=record_id
    )
    if on is not None:
        record.date = on
    target_concept = concept if concept is not None else current_concept
    if concept is not None:
        record.concept_id = concept.id
    if not isinstance(amount, _Unset):
        _apply_amount(record, amount)
    session.flush()
    return _view_from_objects(
        kind, record, target_concept, session.get(User, record.user_id)
    )


def soft_delete_record(session: DbSession, *, kind: str, record_id: int) -> None:
    """Soft-delete one record. No cascade, no undo, no restore."""
    record, _ = load_writable_record(session, kind=kind, record_id=record_id)
    record.is_deleted = True
    session.flush()


def bulk_soft_delete(session: DbSession, *, kind: str, ids: Sequence[int]) -> int:
    """Soft-delete every listed record, all-or-nothing (BACKEND.md § 5.4)."""
    found: dict[int, RecordModel] = {
        record.id: record for record in _records_by_id(session, kind, ids)
    }
    for identifier in ids:
        if identifier not in found:
            raise not_found(NOT_FOUND_MESSAGE)
    for identifier in ids:
        record = found[identifier]
        if record.is_deleted or _concept_is_gone(session, record.concept_id):
            raise gone()
    for identifier in ids:
        found[identifier].is_deleted = True
    session.flush()
    return len(ids)


def _records_by_id(
    session: DbSession, kind: str, ids: Sequence[int]
) -> Sequence[RecordModel]:
    """Fetch the listed records of one kind, whatever their deletion state."""
    if kind == TRANSACTION:
        return session.scalars(select(Transaction).where(Transaction.id.in_(ids))).all()
    return session.scalars(select(Budget).where(Budget.id.in_(ids))).all()


def _fetch_record(session: DbSession, kind: str, record_id: int) -> RecordModel | None:
    """Look one record up by primary key in the table its kind selects."""
    if kind == TRANSACTION:
        return session.get(Transaction, record_id)
    return session.get(Budget, record_id)


def load_concept_for_write(session: DbSession, concept_id: int) -> Concept:
    """Load the concept a new or edited record may point at.

    A missing or deleted concept is a 422 here, not a 410: API_SURFACE.md
    § POST /records specifies VALIDATION_ERROR for both cases.
    """
    concept = session.get(Concept, concept_id)
    if concept is None or concept.is_deleted:
        raise validation_error(MISSING_CONCEPT_MESSAGE)
    return concept


def load_writable_record(
    session: DbSession, *, kind: str, record_id: int
) -> tuple[RecordModel, Concept]:
    """Load a record for editing, mapping absence and deletion onto contract codes."""
    record = _fetch_record(session, kind, record_id)
    if record is None:
        raise not_found(NOT_FOUND_MESSAGE)
    if record.is_deleted:
        raise gone()
    concept = session.get(Concept, record.concept_id)
    if concept is None or concept.is_deleted:
        raise gone()
    return record, concept


def _concept_is_gone(session: DbSession, concept_id: int) -> bool:
    concept = session.get(Concept, concept_id)
    return concept is None or concept.is_deleted


def _new_record(
    kind: str, *, on: date, concept: Concept, amount: Decimal | None, user: User
) -> RecordModel:
    if kind == BUDGET:
        return Budget(date=on, concept_id=concept.id, amount=amount, user_id=user.id)
    if amount is None:
        raise validation_error(AMOUNT_REQUIRED_MESSAGE)
    return Transaction(date=on, concept_id=concept.id, amount=amount, user_id=user.id)


def _apply_amount(record: RecordModel, amount: Decimal | None) -> None:
    if isinstance(record, Budget):
        record.amount = amount
        return
    if amount is None:
        raise validation_error(AMOUNT_REQUIRED_MESSAGE)
    record.amount = amount


def _filtered_query(
    kind: str, *, month: str | None, search: str | None, history: bool
) -> Select[Any]:
    """Build the record query, including the ghost rule for deleted concepts."""
    model = _model_for(kind)
    statement = (
        select(
            model.id.label("record_id"),
            model.date.label("record_date"),
            model.concept_id.label("concept_id"),
            model.amount.label("amount"),
            model.user_id.label("user_id"),
            model.created_at.label("created_at"),
            Concept.name.label("concept_name"),
            Concept.flow.label("concept_flow"),
            Concept.is_deleted.label("concept_is_deleted"),
            User.username.label("username"),
            User.is_deleted.label("user_is_deleted"),
        )
        .join(Concept, model.concept_id == Concept.id)
        .join(User, model.user_id == User.id)
        .where(model.is_deleted.is_(False))
    )
    # Budgets always hide a deleted concept's rows. Transactions hide them only
    # in the working month; history keeps them, flagged.
    if kind == BUDGET or not history:
        statement = statement.where(Concept.is_deleted.is_(False))
    if kind == TRANSACTION and month is not None:
        first_day, last_day = month_bounds(month)
        statement = statement.where(model.date >= first_day, model.date <= last_day)
    if search:
        # Case-insensitive on every backend, and autoescaped so a submitted `%`
        # cannot widen the match.
        statement = statement.where(
            func.lower(Concept.name).contains(search.lower(), autoescape=True)
        )
    # The concrete Select type carries one parameter per selected column, and
    # that tuple changes with the record kind. Callers only ever chain the
    # generic Select operations, so widen once here rather than at every use.
    return cast("Select[Any]", statement)


def _to_view(kind: str, row: RowMapping) -> RecordView:
    return RecordView(
        id=row["record_id"],
        type=kind,
        date=row["record_date"],
        concept_id=row["concept_id"],
        concept_name=row["concept_name"],
        concept_flow=row["concept_flow"],
        concept_is_deleted=bool(row["concept_is_deleted"]),
        amount=row["amount"],
        user_id=row["user_id"],
        username=row["username"],
        user_is_deleted=bool(row["user_is_deleted"]),
        created_at=row["created_at"],
    )


def _view_from_objects(
    kind: str, record: RecordModel, concept: Concept, user: User | None
) -> RecordView:
    return RecordView(
        id=record.id,
        type=kind,
        date=record.date,
        concept_id=concept.id,
        concept_name=concept.name,
        concept_flow=concept.flow,
        concept_is_deleted=bool(concept.is_deleted),
        amount=record.amount,
        user_id=record.user_id,
        username="" if user is None else user.username,
        user_is_deleted=False if user is None else bool(user.is_deleted),
        created_at=record.created_at,
    )
