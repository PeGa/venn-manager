"""History routes.

Read-only access to past months' transaction data.
Rejects current/future month requests.
"""

from datetime import datetime

from flask import Blueprint, jsonify, request

from app import db
from app.middleware.auth import login_required
from app.models.transaction import Transaction
from app.utils.validators import validate_month

history_bp = Blueprint("history", __name__)


@history_bp.route("", methods=["GET"])
@login_required
def get_history() -> tuple:
    """Get transaction history for a past month.

    Query params: month (required, YYYY-MM). Must be a past month.
    Returns 200 with list of TransactionObjects (same shape as /api/records).
    Returns 400 if month is current or future.
    """
    month_str = request.args.get("month")
    if not month_str:
        return jsonify({"error": "BAD_REQUEST", "detail": "month parameter required"}), 400

    try:
        validate_month(month_str)
    except ValueError as e:
        return jsonify({"error": "BAD_REQUEST", "detail": str(e)}), 400

    now = datetime.now()
    current_month_str = now.strftime("%Y-%m")
    if month_str >= current_month_str:
        return jsonify(
            {"error": "BAD_REQUEST", "detail": "History is only available for past months"}
        ), 400

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


@history_bp.route("/months", methods=["GET"])
@login_required
def get_history_months() -> tuple:
    """List months that have at least one transaction record.

    Excludes the current month. Returns months in descending order.
    Returns 200 with { "months": ["YYYY-MM", ...] }.
    """
    now = datetime.now()
    current_month_str = now.strftime("%Y-%m")

    results = (
        db.session.query(
            db.func.strftime("%Y-%m", Transaction.date).label("month")
        )
        .group_by("month")
        .having("month" < current_month_str)
        .order_by(db.desc("month"))
        .all()
    )

    months = [row.month for row in results]
    return jsonify({"months": months}), 200
