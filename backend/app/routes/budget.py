"""Budget routes.

CRUD for planned money movements. Amount is nullable.
Flow derived from Concept. Deletion is hard. Bulk delete capped at 100 IDs.
"""

from datetime import datetime

from flask import Blueprint, jsonify, request
from flask_login import current_user

from app import db
from app.middleware.auth import login_required
from app.models.budget import Budget
from app.models.concept import Concept
from app.utils.validators import validate_amount, validate_date, validate_month

budget_bp = Blueprint("budget", __name__)


@budget_bp.route("", methods=["GET"])
@login_required
def list_budget() -> tuple:
    """List budget entries for a given month sorted by id asc.

    Query params: month (required, YYYY-MM)
    Returns 200 with list of BudgetObjects.
    """
    month_str = request.args.get("month")
    if not month_str:
        return jsonify({"error": "BAD_REQUEST", "detail": "month parameter required"}), 400

    try:
        validate_month(month_str)
    except ValueError as e:
        return jsonify({"error": "BAD_REQUEST", "detail": str(e)}), 400

    year, month = int(month_str[:4]), int(month_str[5:7])
    budgets = (
        Budget.query
        .filter(
            db.extract("year", Budget.date) == year,
            db.extract("month", Budget.date) == month,
        )
        .order_by(Budget.id.asc())
        .all()
    )

    filter_str = request.args.get("filter", "").strip()
    if filter_str:
        budgets = [
            b for b in budgets
            if filter_str.lower() in (b.concept.name or "").lower()
            or filter_str.lower() in (b.user.username or "").lower()
        ]

    return jsonify({"budget": [b.to_dict() for b in budgets]}), 200


@budget_bp.route("", methods=["POST"])
@login_required
def create_budget() -> tuple:
    """Create a new budget entry.

    Body: { "date": string, "concept_id": integer, "amount": number|null }
    Returns 201 with BudgetObject.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "BAD_REQUEST", "detail": "Request body required"}), 400

    try:
        date_val = validate_date(str(data.get("date", "")))
        concept_id = int(data["concept_id"])
        amount = validate_amount(data["amount"]) if data.get("amount") is not None else None
    except (KeyError, TypeError, ValueError) as e:
        return jsonify({"error": "BAD_REQUEST", "detail": str(e)}), 400

    concept = db.session.get(Concept, concept_id)
    if concept is None:
        return jsonify({"error": "NOT_FOUND", "detail": "Concept not found"}), 404
    if concept.is_deleted:
        return jsonify({"error": "BAD_REQUEST", "detail": "Concept has been deleted"}), 400

    budget = Budget(
        date=datetime.strptime(date_val, "%Y-%m-%d").date(),
        concept_id=concept_id,
        amount=amount,
        user_id=current_user.id,
    )
    db.session.add(budget)
    db.session.commit()

    return jsonify(budget.to_dict()), 201


@budget_bp.route("/<int:budget_id>", methods=["PUT"])
@login_required
def update_budget(budget_id: int) -> tuple:
    """Update a budget entry (partial update supported).

    Body: { "date"?: string, "concept_id"?: integer, "amount"?: number|null }
    Returns 200 with updated BudgetObject.
    """
    budget = db.session.get(Budget, budget_id)
    if budget is None:
        return jsonify({"error": "NOT_FOUND", "detail": "Budget entry not found"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "BAD_REQUEST", "detail": "Request body required"}), 400

    try:
        if "date" in data:
            budget.date = datetime.strptime(validate_date(str(data["date"])), "%Y-%m-%d").date()
        if "concept_id" in data:
            concept_id = int(data["concept_id"])
            concept = db.session.get(Concept, concept_id)
            if concept is None:
                return jsonify({"error": "NOT_FOUND", "detail": "Concept not found"}), 404
            if concept.is_deleted:
                return jsonify({"error": "BAD_REQUEST", "detail": "Concept has been deleted"}), 400
            budget.concept_id = concept_id
        if "amount" in data:
            budget.amount = validate_amount(data["amount"]) if data["amount"] is not None else None
    except (TypeError, ValueError) as e:
        return jsonify({"error": "BAD_REQUEST", "detail": str(e)}), 400

    db.session.commit()
    return jsonify(budget.to_dict()), 200


@budget_bp.route("/<int:budget_id>", methods=["DELETE"])
@login_required
def delete_budget(budget_id: int) -> tuple:
    """Hard-delete a budget entry.

    Returns 200 with { "deleted": true }.
    """
    budget = db.session.get(Budget, budget_id)
    if budget is None:
        return jsonify({"error": "NOT_FOUND", "detail": "Budget entry not found"}), 404

    db.session.delete(budget)
    db.session.commit()
    return jsonify({"deleted": True}), 200


@budget_bp.route("/bulk", methods=["DELETE"])
@login_required
def bulk_delete_budget() -> tuple:
    """Hard-delete multiple budget entries.

    Body: { "ids": [integer] }
    Max 100 IDs per request. Non-existent IDs silently ignored.
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
    for budget_id in ids:
        budget = db.session.get(Budget, int(budget_id))
        if budget:
            db.session.delete(budget)
            deleted += 1

    db.session.commit()
    return jsonify({"deleted_count": deleted}), 200
