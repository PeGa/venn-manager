"""Settings routes.

Global currency setting and per-user language/theme preferences.
"""

from flask import Blueprint, jsonify, request
from flask_login import current_user

from app import db
from app.middleware.auth import login_required
from app.models.settings import Settings
from app.utils.validators import validate_currency, validate_theme

settings_bp = Blueprint("settings", __name__)


@settings_bp.route("", methods=["GET"])
@login_required
def get_settings() -> tuple:
    """Get global and per-user settings.

    Returns currency (global), language and theme (per-user).
    """
    settings = Settings.query.first()
    return jsonify({
        "currency": settings.currency if settings else "$",
        "language": current_user.language,
        "theme": current_user.theme,
    }), 200


@settings_bp.route("/currency", methods=["PUT"])
@login_required
def set_currency() -> tuple:
    """Update global currency symbol.

    Body: { "currency": string }
    Any authenticated user may change this. Must be exactly 1 grapheme cluster.
    """
    data = request.get_json()
    if not data or "currency" not in data:
        return jsonify({"error": "BAD_REQUEST", "detail": "currency field required"}), 400

    try:
        currency = validate_currency(str(data["currency"]))
    except ValueError as e:
        return jsonify({"error": "BAD_REQUEST", "detail": str(e)}), 400

    settings = Settings.query.first()
    settings.currency = currency
    db.session.commit()

    return jsonify({"currency": settings.currency}), 200


@settings_bp.route("/language", methods=["PUT"])
@login_required
def set_language() -> tuple:
    """Update per-user language preference.

    Body: { "language": string }
    """
    data = request.get_json()
    if not data or "language" not in data:
        return jsonify({"error": "BAD_REQUEST", "detail": "language field required"}), 400

    language = str(data["language"]).strip()
    if not language:
        return jsonify({"error": "BAD_REQUEST", "detail": "language cannot be empty"}), 400

    current_user.language = language
    db.session.commit()

    return jsonify({"language": current_user.language}), 200


@settings_bp.route("/theme", methods=["PUT"])
@login_required
def set_theme() -> tuple:
    """Update per-user theme preference.

    Body: { "theme": string }
    Must be 'light', 'dark', or 'system'.
    """
    data = request.get_json()
    if not data or "theme" not in data:
        return jsonify({"error": "BAD_REQUEST", "detail": "theme field required"}), 400

    try:
        theme = validate_theme(str(data["theme"]))
    except ValueError as e:
        return jsonify({"error": "BAD_REQUEST", "detail": str(e)}), 400

    current_user.theme = theme
    db.session.commit()

    return jsonify({"theme": current_user.theme}), 200
