"""Response payload builders.

Kept out of routes so every endpoint returns the identical shape for a given
resource, and out of models so persistence stays free of API concerns.
"""

from __future__ import annotations

from typing import Any

from app.models import User
from app.services.concepts import ConceptView
from app.services.records import RecordView


def serialize_user(user: User) -> dict[str, Any]:
    """Render a user for the auth and user-management payloads.

    The password hash is never included.
    """
    return {
        "id": user.id,
        "username": user.username,
        "real_name": user.real_name,
        "is_admin": user.is_admin,
    }


def serialize_concept(view: ConceptView) -> dict[str, Any]:
    """Render a concept, resolving `created_by` to a username.

    `created_by_is_deleted` lets the frontend render the faint "(deleted)" tag
    required by BACKEND.md § 1.2.
    """
    concept = view.concept
    return {
        "id": concept.id,
        "name": concept.name,
        "flow": concept.flow,
        "created_by": view.created_by,
        "created_by_is_deleted": view.created_by_is_deleted,
        "created_at": concept.created_at,
        "is_deleted": concept.is_deleted,
    }


def serialize_record(view: RecordView) -> dict[str, Any]:
    """Render a transaction or budget in the contract's unified record shape.

    Key order matches API_SURFACE.md § Record shape, and `amount` stays a
    `Decimal` so the JSON provider can emit two decimal places.
    """
    return {
        "id": view.id,
        "type": view.type,
        "date": view.date,
        "concept_id": view.concept_id,
        "concept_name": view.concept_name,
        "concept_flow": view.concept_flow,
        "concept_is_deleted": view.concept_is_deleted,
        "amount": view.amount,
        "user_id": view.user_id,
        "username": view.username,
        "user_is_deleted": view.user_is_deleted,
        "created_at": view.created_at,
    }
