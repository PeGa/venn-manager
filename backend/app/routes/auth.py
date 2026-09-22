"""Authentication routes.

Handles login, logout, session check (me), and password change.
Login is the only unauthenticated endpoint. Password change is available
when must_change_password is True (bypasses the usual gate).
"""

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required as flask_login_required, login_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash

from app import db
from app.models.user import User

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["POST"])
def login() -> tuple:
    """Authenticate user and create session.

    Body: { "username": string, "password": string }
    Returns 200 with UserObject on success, 401 on invalid credentials.
    """
    data = request.get_json()
    if not data or "username" not in data or "password" not in data:
        return jsonify({"error": "BAD_REQUEST", "detail": "Username and password required"}), 400

    username = str(data["username"]).strip()
    password = str(data["password"])

    user = User.query.filter_by(username=username).first()
    if user is None or not check_password_hash(user.password_hash, password):
        return jsonify({"error": "UNAUTHORIZED", "detail": "Invalid credentials"}), 401

    login_user(user)
    return jsonify({"user": user.to_dict(include_sensitive=True)}), 200


@auth_bp.route("/logout", methods=["POST"])
@flask_login_required
def logout() -> tuple:
    """Destroy session server-side and clear cookie.

    Returns 200 on success, 401 if no valid session.
    """
    logout_user()
    return jsonify({"ok": True}), 200


@auth_bp.route("/me", methods=["GET"])
@flask_login_required
def me() -> tuple:
    """Return current user info including must_change_password flag.

    This endpoint is available even when must_change_password is True,
    so the frontend can detect the forced password-change flow.
    """
    return jsonify({"user": current_user.to_dict(include_sensitive=True)}), 200


@auth_bp.route("/change-password", methods=["POST"])
@flask_login_required
def change_password() -> tuple:
    """Change current user's password.

    Body: { "current_password": string, "new_password": string }
    Clears must_change_password flag if it was set.
    Returns 200 on success, 401 if current password wrong, 400 if new password invalid.
    """
    data = request.get_json()
    if not data or "current_password" not in data or "new_password" not in data:
        return jsonify({"error": "BAD_REQUEST", "detail": "Current and new password required"}), 400

    current_password = str(data["current_password"])
    new_password = str(data["new_password"]).strip()

    if not new_password:
        return jsonify({"error": "BAD_REQUEST", "detail": "New password cannot be empty"}), 400

    if not check_password_hash(current_user.password_hash, current_password):
        return jsonify({"error": "UNAUTHORIZED", "detail": "Current password is incorrect"}), 401

    current_user.password_hash = generate_password_hash(new_password)
    current_user.must_change_password = False
    db.session.commit()

    return jsonify({"ok": True}), 200
