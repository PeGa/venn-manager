"""Month switch routes.

Detects new month availability and performs the month switch,
updating budget entry dates with day clamping.
"""

import calendar
from datetime import datetime

from flask import Blueprint, jsonify

from app import db
from app.middleware.auth import login_required
from app.models.budget import Budget

month_bp = Blueprint("month", __name__)


@month_bp.route("/status", methods=["GET"])
@login_required
def month_status() -> tuple:
    """Get current month status for polling.

    Returns:
      - current_month: server's current YYYY-MM
      - active_month: the month the app is operating in
      - switch_available: true if current_month > active_month
    """
    current_month = datetime.now().strftime("%Y-%m")
    active_month = _get_active_month()

    return jsonify({
        "current_month": current_month,
        "active_month": active_month,
        "switch_available": current_month > active_month,
    }), 200


@month_bp.route("/switch", methods=["POST"])
@login_required
def month_switch() -> tuple:
    """Perform month switch.

    Updates all budget entry dates to the new month with day clamping.
    Returns 200 with { "switched": true, "new_month": string }.
    Returns 400 if no switch is available.
    """
    current_month = datetime.now().strftime("%Y-%m")
    active_month = _get_active_month()

    if current_month <= active_month:
        return jsonify({"error": "BAD_REQUEST", "detail": "No month switch available"}), 400

    new_year, new_month_num = int(current_month[:4]), int(current_month[5:7])

    # Update all budget dates with day clamping
    budgets = Budget.query.all()
    for budget in budgets:
        old_day = budget.date.day
        max_day = calendar.monthrange(new_year, new_month_num)[1]
        clamped_day = min(old_day, max_day)
        budget.date = budget.date.replace(year=new_year, month=new_month_num, day=clamped_day)

    db.session.commit()

    return jsonify({"switched": True, "new_month": current_month}), 200


def _get_active_month() -> str:
    """Determine the currently active month.

    Uses the most recent budget entry date, or falls back to the
    most recent transaction date, or the current month if nothing exists.
    """
    latest_budget = Budget.query.order_by(Budget.date.desc()).first()
    if latest_budget:
        return latest_budget.date.strftime("%Y-%m")

    from app.models.transaction import Transaction
    latest_transaction = Transaction.query.order_by(Transaction.date.desc()).first()
    if latest_transaction:
        return latest_transaction.date.strftime("%Y-%m")

    return datetime.now().strftime("%Y-%m")
