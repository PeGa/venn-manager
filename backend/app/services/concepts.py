"""Concept rules (API_SURFACE.md § 3.3, BACKEND.md § 1.2 and § 5.2).

Two invariants live here: `flow` is immutable after creation, and deleting a
concept never cascades — referencing transactions and budgets keep
`is_deleted = false`, and their visibility is derived from the concept's state.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import select

from app.extensions import DbSession
from app.models import Concept, User
from app.services.errors import conflict, gone, not_found

NOT_FOUND_MESSAGE = "Concept not found"
DUPLICATE_MESSAGE = "A concept with this name and flow already exists"


@dataclass(frozen=True)
class ConceptView:
    """A concept plus the creator fields the API resolves alongside it.

    Resolved with one join instead of a relationship so a concept list never
    triggers a query per row (AGENTS.md § Performance Guardrails).
    """

    concept: Concept
    created_by: str | None
    created_by_is_deleted: bool


def list_concepts(
    session: DbSession, *, flow: str | None = None, include_deleted: bool = False
) -> list[ConceptView]:
    """Return concepts ordered by id, optionally filtered by flow."""
    statement = (
        select(Concept, User.username, User.is_deleted)
        .outerjoin(User, Concept.created_by == User.id)
        .order_by(Concept.id)
    )
    if flow is not None:
        statement = statement.where(Concept.flow == flow)
    if not include_deleted:
        statement = statement.where(Concept.is_deleted.is_(False))
    return [
        ConceptView(concept, username, bool(creator_is_deleted))
        for concept, username, creator_is_deleted in session.execute(statement).all()
    ]


def get_concept(session: DbSession, concept_id: int) -> ConceptView | None:
    """Return one concept with its creator resolved, or None when absent."""
    row = session.execute(
        select(Concept, User.username, User.is_deleted)
        .outerjoin(User, Concept.created_by == User.id)
        .where(Concept.id == concept_id)
    ).first()
    if row is None:
        return None
    return ConceptView(row[0], row[1], bool(row[2]))


def get_writable_concept(session: DbSession, concept_id: int) -> ConceptView:
    """Load a concept for writing: 404 when absent, 410 when soft-deleted."""
    view = get_concept(session, concept_id)
    if view is None:
        raise not_found(NOT_FOUND_MESSAGE)
    if view.concept.is_deleted:
        raise gone()
    return view


def create_concept(
    session: DbSession, *, name: str, flow: str, creator: User
) -> ConceptView:
    """Create a concept. Flushes; the caller commits."""
    if _duplicate_exists(session, name=name, flow=flow):
        raise conflict(DUPLICATE_MESSAGE)
    concept = Concept(name=name, flow=flow, created_by=creator.id)
    session.add(concept)
    session.flush()
    return ConceptView(concept, creator.username, bool(creator.is_deleted))


def rename_concept(session: DbSession, concept_id: int, *, name: str) -> ConceptView:
    """Rename a concept. The flow stays untouched.

    Renaming is not a cascade: records store `concept_id`, so the new name
    resolves everywhere immediately (BACKEND.md § 5.2).
    """
    view = get_writable_concept(session, concept_id)
    if _duplicate_exists(
        session, name=name, flow=view.concept.flow, exclude_id=concept_id
    ):
        raise conflict(DUPLICATE_MESSAGE)
    view.concept.name = name
    session.flush()
    return view


def soft_delete_concept(session: DbSession, concept_id: int) -> None:
    """Soft-delete a concept without touching the records that reference it."""
    view = get_writable_concept(session, concept_id)
    view.concept.is_deleted = True
    session.flush()


def bulk_soft_delete(session: DbSession, concept_ids: Sequence[int]) -> int:
    """Soft-delete every listed concept, all-or-nothing.

    BACKEND.md § 5.4: a missing id is 404 and an already-deleted id is 410, and
    in either case nothing is written.
    """
    found = {
        concept.id: concept
        for concept in session.scalars(
            select(Concept).where(Concept.id.in_(concept_ids))
        ).all()
    }
    for identifier in concept_ids:
        if identifier not in found:
            raise not_found(NOT_FOUND_MESSAGE)
    for identifier in concept_ids:
        if found[identifier].is_deleted:
            raise gone()
    for identifier in concept_ids:
        found[identifier].is_deleted = True
    session.flush()
    return len(concept_ids)


def _duplicate_exists(
    session: DbSession, *, name: str, flow: str, exclude_id: int | None = None
) -> bool:
    """True when a *non-deleted* concept already uses this name and flow.

    Uniqueness is per (name, flow): API_SURFACE.md § POST concepts allows the
    same name under the other flow, and a deleted concept's name is reusable.
    """
    statement = select(Concept.id).where(
        Concept.name == name, Concept.flow == flow, Concept.is_deleted.is_(False)
    )
    if exclude_id is not None:
        statement = statement.where(Concept.id != exclude_id)
    return session.scalar(statement) is not None
