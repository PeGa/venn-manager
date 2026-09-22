"""Transaction (Home screen) routes.

CRUD for actual money movements. Flow is derived from Concept, not stored.
Deletion is hard. Bulk delete capped at 100 IDs.
"""

from datetime import datetime

from flask import Blueprint, jsonify, request
from flask_login import current_user

from app import db
from app.middleware.auth import login_required
from app.models.concept import Concept
from app.models.transaction import Transaction
from app.utils.validators import validate_amount, validate_date

records_bp = Blueprint("records", __name__)


@records_bp.route("", methods=["GET"])
@login_required
def list_records() -> tuple:
    """List transactions for a given month.

    Query params: month (required, YYYY-MM)
    Returns 200 with list of TransactionObjects sorted by id asc.
    """
    month_str = request.args.get("month")
    if not month_str:
        return jsonify({"error": "BAD_REQUEST", "detail": "month parameter required"}), 400

    from app.utils.validators import validate_month
    try:
        validate_month(month_str)
    except ValueError as e:
        return jsonify({"error": "BAD_REQUEST", "detail": str(e)}), 400

    year, month = int(month_str[:4]), int(month_str[5:7])
    transactions = (
        Transaction.query
        .filter(
            db.extract("year", Transaction.date) == year,
            db.extract("month", Transaction.date) == month,
        )
        .order_by(Transaction.id.asc())
        .all()
    )

    filter_str = request.args.get("filter", "").strip()
    if filter_str:
        transactions = [
            t for t in transactions
            if filter_str.lower() in (t.concept.name or "").lower()
            or filter_str.lower() in (t.user.username or "").lower()
        ]

    return jsonify({"records": [t.to_dict() for t in transactions]}), 200


@records_bp.route("", methods=["POST"])
@login_required
def create_record() -> tuple:
    """Create a new transaction.

    Body: { "date": string, "concept_id": integer, "amount": number }
    Flow is derived from the concept. user_id from session.
    Returns 201 with TransactionObject.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "BAD_REQUEST", "detail": "Request body required"}), 400

    try:
        date_val = validate_date(str(data.get("date", "")))
        concept_id = int(data["concept_id"])
        amount = validate_amount(data["amount"])
    except (KeyError, TypeError, ValueError) as e:
        return jsonify({"error": "BAD_REQUEST", "detail": str(e)}), 400

    concept = db.session.get(Concept, concept_id)
    if concept is None:
        return jsonify({"error": "NOT_FOUND", "detail": "Concept not found"}), 404
    if concept.is_deleted:
        return jsonify({"error": "BAD_REQUEST", "detail": "Concept has been deleted"}), 400

    transaction = Transaction(
        date=datetime.strptime(date_val, "%Y-%m-%d").date(),
        concept_id=concept_id,
        amount=amount,
        user_id=current_user.id,
    )
    db.session.add(transaction)
    db.session.commit()

    return jsonify(transaction.to_dict()), 201


@records_bp.route("/<int:record_id>", methods=["PUT"])
@login_required
def update_record(record_id: int) -> tuple:
    """Update a transaction (partial update supported).

    Body: { "date"?: string, "concept_id"?: integer, "amount"?: number }
    Returns 200 with updated TransactionObject.
    """
    transaction = db.session.get(Transaction, record_id)
    if transaction is None:
        return jsonify({"error": "NOT_FOUND", "detail": "Record not found"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "BAD_REQUEST", "detail": "Request body required"}), 400

    try:
        if "date" in data:
            transaction.date = datetime.strptime(validate_date(str(data["date"])), "%Y-%m-%d").date()
        if "concept_id" in data:
            concept_id = int(data["concept_id"])
            concept = db.session.get(Concept, concept_id)
            if concept is None:
                return jsonify({"error": "NOT_FOUND", "detail": "Concept not found"}), 404
            if concept.is_deleted:
                return jsonify({"error": "BAD_REQUEST", "detail": "Concept has been deleted"}), 400
            transaction.concept_id = concept_id
        if "amount" in data:
            transaction.amount = validate_amount(data["amount"])
    except (TypeError, ValueError) as e:
        return jsonify({"error": "BAD_REQUEST", "detail": str(e)}), 400

    db.session.commit()
    return jsonify(transaction.to_dict()), 200


@records_bp.route("/<int:record_id>", methods=["DELETE"])
@login_required
def delete_record(record_id: int) -> tuple:
    """Hard-delete a transaction.

    Returns 200 with { "deleted": true }.
    """
    transaction = db.session.get(Transaction, record_id)
    if transaction is None:
        return jsonify({"error": "NOT_FOUND", "detail": "Record not found"}), 404

    db.session.delete(transaction)
    db.session.commit()
    return jsonify({"deleted": True}), 200


@records_bp.route("/bulk", methods=["DELETE"])
@login_required
def bulk_delete_records() -> tuple:
    """Hard-delete multiple transactions.

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
    for record_id in ids:
        transaction = db.session.get(Transaction, int(record_id))
        if transaction:
            db.session.delete(transaction)
            deleted += 1

    db.session.commit()
    return jsonify({"deleted_count": deleted}), 200
