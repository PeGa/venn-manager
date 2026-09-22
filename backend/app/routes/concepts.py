"""Concept routes.

CRUD for accounting concepts. Flow is immutable after creation.
Deletion is soft (is_deleted=True). Bulk delete capped at 100 IDs.
"""

from flask import Blueprint, jsonify, request
from flask_login import current_user

from app import db
from app.middleware.auth import login_required
from app.models.concept import Concept
from app.utils.validators import validate_flow, validate_string

concepts_bp = Blueprint("concepts", __name__)


@concepts_bp.route("", methods=["GET"])
@login_required
def list_concepts() -> tuple:
    """List all non-deleted concepts sorted by id asc.

    Supports optional 'filter' query param for substring search on name/username.
    Returns 200 with list of ConceptObjects.
    """
    query = Concept.query.filter_by(is_deleted=False)

    filter_str = request.args.get("filter", "").strip()
    concepts = query.order_by(Concept.id.asc()).all()

    if filter_str:
        concepts = [
            c for c in concepts
            if filter_str.lower() in c.name.lower()
            or filter_str.lower() in (c.created_by_user.username or "").lower()
        ]

    return jsonify({"concepts": [c.to_dict() for c in concepts]}), 200


@concepts_bp.route("", methods=["POST"])
@login_required
def create_concept() -> tuple:
    """Create a new concept.

    Body: { "name": string, "flow": "IN"|"OUT" }
    Rejects duplicate name among non-deleted concepts.
    Returns 201 with ConceptObject.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "BAD_REQUEST", "detail": "Request body required"}), 400

    try:
        name = validate_string(data.get("name", ""), 64, "name")
        flow = validate_flow(data.get("flow", ""))
    except ValueError as e:
        return jsonify({"error": "BAD_REQUEST", "detail": str(e)}), 400

    existing = Concept.query.filter_by(name=name, flow=flow, is_deleted=False).first()
    if existing:
        return jsonify({"error": "CONFLICT", "detail": "Concept with this name already exists"}), 409

    concept = Concept(
        name=name,
        flow=flow,
        created_by=current_user.id,
    )
    db.session.add(concept)
    db.session.commit()

    return jsonify(concept.to_dict()), 201


@concepts_bp.route("/<int:concept_id>", methods=["PUT"])
@login_required
def update_concept(concept_id: int) -> tuple:
    """Update a concept's name only. Flow is immutable.

    Body: { "name": string }
    Rejects if body contains 'flow' field.
    Returns 200 with updated ConceptObject.
    """
    concept = db.session.get(Concept, concept_id)
    if concept is None or concept.is_deleted:
        return jsonify({"error": "NOT_FOUND", "detail": "Concept not found"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "BAD_REQUEST", "detail": "Request body required"}), 400

    if "flow" in data:
        return jsonify(
            {"error": "BAD_REQUEST", "detail": "Flow is immutable. Delete and recreate to change flow."}
        ), 400

    try:
        name = validate_string(data.get("name", ""), 64, "name")
    except ValueError as e:
        return jsonify({"error": "BAD_REQUEST", "detail": str(e)}), 400

    existing = Concept.query.filter_by(name=name, flow=concept.flow, is_deleted=False).first()
    if existing and existing.id != concept_id:
        return jsonify({"error": "CONFLICT", "detail": "Concept with this name already exists"}), 409

    concept.name = name
    db.session.commit()

    return jsonify(concept.to_dict()), 200


@concepts_bp.route("/<int:concept_id>", methods=["DELETE"])
@login_required
def delete_concept(concept_id: int) -> tuple:
    """Soft-delete a concept.

    Returns 200 with { "deleted": true }.
    """
    concept = db.session.get(Concept, concept_id)
    if concept is None or concept.is_deleted:
        return jsonify({"error": "NOT_FOUND", "detail": "Concept not found"}), 404

    concept.is_deleted = True
    db.session.commit()
    return jsonify({"deleted": True}), 200


@concepts_bp.route("/bulk", methods=["DELETE"])
@login_required
def bulk_delete_concepts() -> tuple:
    """Soft-delete multiple concepts.

    Body: { "ids": [integer] }
    Max 100 IDs per request. Non-existent/already-deleted IDs silently ignored.
    Returns 200 with { "deleted_count": integer }.
    """
    data = request.get_json()
    if not data or "ids" not in data:
        return jsonify({"error": "BAD_REQUEST", "detail": "ids array required"}), 400

    ids = data["ids"]
    if not isinstance(ids, list) or len(ids) == 0:
        return jsonify({"error": "BAD_REQUEST", "detail": "ids must be a non-empty array"}), 400
    if len(ids) > 100:
        return jsonify({"error": "BAD_REQUEST", "detail": "Maximum 100 IDs per request"}), 400

    deleted = 0
    for concept_id in ids:
        concept = db.session.get(Concept, int(concept_id))
        if concept and not concept.is_deleted:
            concept.is_deleted = True
            deleted += 1

    db.session.commit()
    return jsonify({"deleted_count": deleted}), 200
