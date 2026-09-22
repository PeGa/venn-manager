"""Projection calculation routes.

Computes the five widget values for the Home screen dashboard.
Uses fixed-precision Decimal arithmetic throughout.
"""

from decimal import Decimal

from flask import Blueprint, jsonify, request

from app import db
from app.middleware.auth import login_required
from app.models.budget import Budget
from app.models.concept import Concept
from app.models.transaction import Transaction
from app.utils.validators import validate_month

projections_bp = Blueprint("projections", __name__)


@projections_bp.route("", methods=["GET"])
@login_required
def get_projections() -> tuple:
    """Compute projection values for a given month.

    Query params: month (required, YYYY-MM)
    Returns 200 with:
      - current_out: actual spending so far
      - current_in: actual earnings so far
      - spend_projection: pessimistic spend forecast
      - earn_projection: pessimistic earn forecast
      - savings_projection: earn - spend
    """
    month_str = request.args.get("month")
    if not month_str:
        return jsonify({"error": "BAD_REQUEST", "detail": "month parameter required"}), 400

    try:
        validate_month(month_str)
    except ValueError as e:
        return jsonify({"error": "BAD_REQUEST", "detail": str(e)}), 400

    year, month = int(month_str[:4]), int(month_str[5:7])

    # Fetch budget entries with non-null amounts for this month
    budgets = (
        Budget.query
        .filter(
            db.extract("year", Budget.date) == year,
            db.extract("month", Budget.date) == month,
            Budget.amount.isnot(None),
        )
        .all()
    )

    # Fetch all transactions for this month
    transactions = (
        Transaction.query
        .filter(
            db.extract("year", Transaction.date) == year,
            db.extract("month", Transaction.date) == month,
        )
        .all()
    )

    # Build actual amounts per concept
    actual_by_concept: dict[int, Decimal] = {}
    for t in transactions:
        cid = t.concept_id
        actual_by_concept[cid] = actual_by_concept.get(cid, Decimal("0")) + t.amount

    # Build budget map: concept_id -> (budget_amount, flow)
    budget_map: dict[int, tuple[Decimal, str]] = {}
    for b in budgets:
        concept = db.session.get(Concept, b.concept_id)
        if concept:
            budget_map[b.concept_id] = (b.amount, concept.flow)

    # Budgeted concept IDs
    budgeted_concept_ids = set(budget_map.keys())

    # Spend projection: sum(max(budget, actual)) for OUT + unbudgeted OUT
    spend_projection = Decimal("0")
    for cid, (budget_amount, flow) in budget_map.items():
        if flow == "OUT":
            actual = actual_by_concept.get(cid, Decimal("0"))
            spend_projection += max(budget_amount, actual)

    # Unbudgeted OUT transactions
    for t in transactions:
        if t.concept_id not in budgeted_concept_ids:
            concept = db.session.get(Concept, t.concept_id)
            if concept and concept.flow == "OUT":
                spend_projection += t.amount

    # Earn projection: sum(min(budget, actual)) for IN + unbudgeted IN
    earn_projection = Decimal("0")
    for cid, (budget_amount, flow) in budget_map.items():
        if flow == "IN":
            actual = actual_by_concept.get(cid, Decimal("0"))
            earn_projection += min(budget_amount, actual)

    # Unbudgeted IN transactions
    for t in transactions:
        if t.concept_id not in budgeted_concept_ids:
            concept = db.session.get(Concept, t.concept_id)
            if concept and concept.flow == "IN":
                earn_projection += t.amount

    # Current actuals
    current_out = sum(
        (t.amount for t in transactions if _get_flow(t) == "OUT"),
        Decimal("0"),
    )
    current_in = sum(
        (t.amount for t in transactions if _get_flow(t) == "IN"),
        Decimal("0"),
    )

    savings_projection = earn_projection - spend_projection

    return jsonify({
        "current_out": float(current_out.quantize(Decimal("0.01"))),
        "current_in": float(current_in.quantize(Decimal("0.01"))),
        "spend_projection": float(spend_projection.quantize(Decimal("0.01"))),
        "earn_projection": float(earn_projection.quantize(Decimal("0.01"))),
        "savings_projection": float(savings_projection.quantize(Decimal("0.01"))),
    }), 200


def _get_flow(transaction: Transaction) -> str:
    """Derive flow from the transaction's concept."""
    return transaction.concept.flow if transaction.concept else "OUT"
