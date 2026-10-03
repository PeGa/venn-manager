"""Concept management — API_SURFACE.md § 3.3.

| Method | Route                        | Auth | Purpose                        |
|--------|------------------------------|------|--------------------------------|
| GET    | /settings/concepts           | yes  | List concepts (not paginated)  |
| POST   | /settings/concepts           | yes  | Create a concept               |
| PATCH  | /settings/concepts/:id       | yes  | Rename; flow is immutable      |
| DELETE | /settings/concepts/:id       | yes  | Soft-delete one concept        |
| DELETE | /settings/concepts?ids=      | yes  | Bulk soft-delete (max 100)     |

Errors: 401 `UNAUTHORIZED`, 403 `PASSWORD_CHANGE_REQUIRED`, 404 `NOT_FOUND`,
409 `CONFLICT` (duplicate name and flow), 410 `GONE`, 422 `VALIDATION_ERROR`.
"""

from __future__ import annotations

from typing import Any

from flask import Blueprint, request

from app.extensions import db
from app.middleware.auth import authenticated_user, login_required
from app.middleware.requests import boolean_query, json_body, optional_query
from app.middleware.responses import respond
from app.models.concept import CONCEPT_NAME_MAX_LENGTH, FLOWS
from app.services.concepts import (
    bulk_soft_delete,
    create_concept,
    list_concepts,
    rename_concept,
    soft_delete_concept,
)
from app.services.errors import validation_error
from app.services.serializers import serialize_concept
from app.utils.validation import parse_id_list, require_string, validate_choice

concepts_bp = Blueprint("concepts", __name__)

IMMUTABLE_FLOW_MESSAGE = "Field 'flow' cannot be changed after creation"
NO_FIELDS_MESSAGE = "At least one field must be provided"
UNKNOWN_FIELDS_MESSAGE = "Request contains unknown fields"


@concepts_bp.get("/settings/concepts")
@login_required
def list_all() -> Any:
    """List concepts, newest last. Never paginated, so `meta` is null.

    Query: `flow=in|out` and `include_deleted=true|false` (default false).
    The Concepts screen passes `include_deleted=true` to render deleted rows
    with a faint "(deleted)" tag; pickers use the default list.
    """
    flow = optional_query(request, "flow")
    if flow is not None:
        validate_choice(flow, "flow", FLOWS)
    views = list_concepts(
        db.session, flow=flow, include_deleted=boolean_query(request, "include_deleted")
    )
    return respond([serialize_concept(view) for view in views])


@concepts_bp.post("/settings/concepts")
@login_required
def create() -> Any:
    """Create a concept.

    Request: `{name (<=64 chars), flow: "in"|"out"}`. Response 201: the created
    concept. A duplicate name *and* flow among non-deleted concepts is 409; a
    deleted concept's name may be reused.
    """
    payload = json_body(request)
    view = create_concept(
        db.session,
        name=require_string(payload, "name", max_length=CONCEPT_NAME_MAX_LENGTH),
        flow=validate_choice(payload.get("flow"), "flow", FLOWS),
        creator=authenticated_user(),
    )
    db.session.commit()
    return respond(serialize_concept(view), status=201)


@concepts_bp.patch("/settings/concepts/<int:concept_id>")
@login_required
def rename(concept_id: int) -> Any:
    """Rename a concept.

    Request: `{name}` only. Submitting `flow` is 422 — change the flow by
    deleting the concept and creating a new one (BACKEND.md § 5.2).
    Response 200: the updated concept.
    """
    payload = json_body(request)
    if "flow" in payload:
        raise validation_error(IMMUTABLE_FLOW_MESSAGE)
    if not payload:
        raise validation_error(NO_FIELDS_MESSAGE)
    if set(payload) - {"name"}:
        raise validation_error(UNKNOWN_FIELDS_MESSAGE)

    view = rename_concept(
        db.session,
        concept_id,
        name=require_string(payload, "name", max_length=CONCEPT_NAME_MAX_LENGTH),
    )
    db.session.commit()
    return respond(serialize_concept(view))


@concepts_bp.delete("/settings/concepts/<int:concept_id>")
@login_required
def delete_one(concept_id: int) -> Any:
    """Soft-delete one concept.

    Response 200: `data: null`. Referencing transactions and budgets are not
    mutated; their visibility is derived (BACKEND.md § 1.2).
    """
    soft_delete_concept(db.session, concept_id)
    db.session.commit()
    return respond()


@concepts_bp.delete("/settings/concepts")
@login_required
def delete_many() -> Any:
    """Bulk soft-delete for the Concepts screen's multi-select.

    Query: `ids` — 1 to 100 comma-separated ids. All-or-nothing: a missing id
    is 404, an already-deleted id is 410, and nothing is written in either case.
    Response 200: `{"deleted": <count>}`.
    """
    deleted = bulk_soft_delete(db.session, parse_id_list(request.args.get("ids")))
    db.session.commit()
    return respond({"deleted": deleted})
