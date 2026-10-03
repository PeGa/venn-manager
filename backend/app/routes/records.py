"""Records — API_SURFACE.md § 4.

| Method | Route                    | Auth | Purpose                              |
|--------|--------------------------|------|--------------------------------------|
| GET    | /records                 | yes  | List transactions or budgets         |
| POST   | /records                 | yes  | Create either kind                   |
| PATCH  | /records/:id?type=       | yes  | Partial update                       |
| DELETE | /records/:id?type=       | yes  | Soft-delete one                      |
| DELETE | /records?type=&ids=      | yes  | Bulk soft-delete (max 100)           |

Errors: 401 `UNAUTHORIZED`, 403 `PASSWORD_CHANGE_REQUIRED`, 404 `NOT_FOUND`,
410 `GONE` (record or its concept soft-deleted), 422 `VALIDATION_ERROR`.
"""

from __future__ import annotations

from typing import Any

from flask import Blueprint, request

from app.extensions import db
from app.middleware.auth import authenticated_user, login_required
from app.middleware.requests import (
    json_body,
    optional_query,
    parse_pagination,
    require_query,
    today,
)
from app.middleware.responses import respond
from app.services.errors import validation_error
from app.services.records import (
    BUDGET,
    RECORD_TYPES,
    TRANSACTION,
    bulk_soft_delete,
    create_record,
    list_records,
    load_concept_for_write,
    soft_delete_record,
    update_record,
)
from app.services.serializers import serialize_record
from app.services.settings import working_month
from app.utils.validation import (
    parse_amount,
    parse_date,
    parse_id_list,
    parse_int,
    parse_month,
    validate_choice,
)

records_bp = Blueprint("records", __name__)

EDITABLE_RECORD_FIELDS = frozenset({"date", "concept_id", "amount"})

NO_FIELDS_MESSAGE = "At least one field must be provided"
UNKNOWN_FIELDS_MESSAGE = "Request contains unknown fields"


@records_bp.get("/records")
@login_required
def index() -> Any:
    """List records of one type.

    Query: `type` (required), `month` (required for transactions, ignored for
    budgets), `page`, `q` (`10`/`20`/`50`/`all`), `search`. Results are sorted
    by id ascending and cannot be re-sorted.
    """
    user = authenticated_user()
    kind = validate_choice(require_query(request, "type"), "type", RECORD_TYPES)
    month: str | None = None
    working: str | None = None
    if kind == TRANSACTION:
        month = parse_month(require_query(request, "month"))
        working = working_month(db.session, user.id, today())

    rows, meta = list_records(
        db.session,
        kind=kind,
        pagination=parse_pagination(request),
        month=month,
        search=optional_query(request, "search"),
        working_month=working,
    )
    return respond([serialize_record(row) for row in rows], meta=meta)


@records_bp.post("/records")
@login_required
def create() -> Any:
    """Create a record.

    Request: `{type, date, concept_id, amount?}`. `amount` is required for a
    transaction and nullable for a budget. `flow` is inherited from the concept
    and `user_id` comes from the session; both are ignored if submitted.
    Response 201: the created record.
    """
    user = authenticated_user()
    payload = json_body(request)
    kind = validate_choice(payload.get("type"), "type", RECORD_TYPES)
    view = create_record(
        db.session,
        kind=kind,
        on=parse_date(payload.get("date")),
        concept=load_concept_for_write(
            db.session, parse_int(payload.get("concept_id"), field="concept_id")
        ),
        amount=parse_amount(payload.get("amount"), nullable=kind == BUDGET),
        user=user,
    )
    db.session.commit()
    return respond(serialize_record(view), status=201)


@records_bp.patch("/records/<int:record_id>")
@login_required
def update(record_id: int) -> Any:
    """Partially update a record.

    Query: `type` (required) selects the table. Request: any non-empty subset of
    `{date, concept_id, amount}`. Response 200: the updated record.
    """
    kind = validate_choice(require_query(request, "type"), "type", RECORD_TYPES)
    payload = json_body(request)
    if not payload:
        raise validation_error(NO_FIELDS_MESSAGE)
    if set(payload) - EDITABLE_RECORD_FIELDS:
        raise validation_error(UNKNOWN_FIELDS_MESSAGE)

    changes: dict[str, Any] = {}
    if "date" in payload:
        changes["on"] = parse_date(payload["date"])
    if "concept_id" in payload:
        changes["concept"] = load_concept_for_write(
            db.session, parse_int(payload["concept_id"], field="concept_id")
        )
    if "amount" in payload:
        changes["amount"] = parse_amount(payload["amount"], nullable=kind == BUDGET)

    view = update_record(db.session, kind=kind, record_id=record_id, **changes)
    db.session.commit()
    return respond(serialize_record(view))


@records_bp.delete("/records/<int:record_id>")
@login_required
def delete_one(record_id: int) -> Any:
    """Soft-delete one record. Query: `type` (required). Response 200: null."""
    kind = validate_choice(require_query(request, "type"), "type", RECORD_TYPES)
    soft_delete_record(db.session, kind=kind, record_id=record_id)
    db.session.commit()
    return respond()


@records_bp.delete("/records")
@login_required
def delete_many() -> Any:
    """Bulk soft-delete for the Home and Budget multi-select.

    Query: `type` and `ids` (1 to 100). All-or-nothing. Response 200:
    `{"deleted": <count>}`.
    """
    kind = validate_choice(require_query(request, "type"), "type", RECORD_TYPES)
    deleted = bulk_soft_delete(
        db.session, kind=kind, ids=parse_id_list(request.args.get("ids"))
    )
    db.session.commit()
    return respond({"deleted": deleted})
