"""User management routes (admin only).

CRUD for users. Restricted to admin role.
Prevents deletion of the last admin user.
"""

from flask import Blueprint, jsonify, request
from werkzeug.security import generate_password_hash

from app import db
from app.middleware.auth import admin_required, login_required
from app.models.user import User
from app.utils.validators import validate_string

users_bp = Blueprint("users", __name__)


@users_bp.before_request
@login_required
def require_login() -> None:
    """Ensure all user management routes require authentication."""
    pass


@users_bp.route("", methods=["GET"])
@admin_required
def list_users() -> tuple:
    """List all users. Admin only.

    Returns 200 with list of UserObjects (no password_hash or must_change_password).
    """
    users = User.query.order_by(User.id.asc()).all()
    return jsonify({"users": [u.to_dict() for u in users]}), 200


@users_bp.route("", methods=["POST"])
@admin_required
def create_user() -> tuple:
    """Create a new user. Admin only.

    Body: { "username": string, "real_name": string, "password": string, "is_admin": boolean }
    New users have must_change_password=False.
    Returns 201 with UserObject.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "BAD_REQUEST", "detail": "Request body required"}), 400

    try:
        username = validate_string(data.get("username", ""), 80, "username")
        real_name = validate_string(data.get("real_name", ""), 120, "real_name")
        password = str(data.get("password", "")).strip()
        if not password:
            raise ValueError("password is required")
        is_admin = bool(data.get("is_admin", False))
    except (TypeError, ValueError) as e:
        return jsonify({"error": "BAD_REQUEST", "detail": str(e)}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"error": "CONFLICT", "detail": "Username already exists"}), 409

    user = User(
        username=username,
        real_name=real_name,
        password_hash=generate_password_hash(password),
        is_admin=is_admin,
        must_change_password=False,
    )
    db.session.add(user)
    db.session.commit()

    return jsonify(user.to_dict()), 201


@users_bp.route("/<int:user_id>", methods=["PUT"])
@admin_required
def update_user(user_id: int) -> tuple:
    """Update a user (partial update). Admin only.

    Body: { "username"?: string, "real_name"?: string, "password"?: string, "is_admin"?: boolean }
    Returns 200 with updated UserObject.
    """
    user = db.session.get(User, user_id)
    if user is None:
        return jsonify({"error": "NOT_FOUND", "detail": "User not found"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "BAD_REQUEST", "detail": "Request body required"}), 400

    try:
        if "username" in data:
            username = validate_string(data["username"], 80, "username")
            existing = User.query.filter_by(username=username).first()
            if existing and existing.id != user_id:
                return jsonify({"error": "CONFLICT", "detail": "Username already exists"}), 409
            user.username = username
        if "real_name" in data:
            user.real_name = validate_string(data["real_name"], 120, "real_name")
        if "password" in data:
            password = str(data["password"]).strip()
            if not password:
                raise ValueError("password cannot be empty")
            user.password_hash = generate_password_hash(password)
        if "is_admin" in data:
            user.is_admin = bool(data["is_admin"])
    except (TypeError, ValueError) as e:
        return jsonify({"error": "BAD_REQUEST", "detail": str(e)}), 400

    db.session.commit()
    return jsonify(user.to_dict()), 200


@users_bp.route("/<int:user_id>", methods=["DELETE"])
@admin_required
def delete_user(user_id: int) -> tuple:
    """Hard-delete a user. Admin only.

    Prevents deletion of the last remaining admin.
    Returns 200 with { "deleted": true }.
    """
    user = db.session.get(User, user_id)
    if user is None:
        return jsonify({"error": "NOT_FOUND", "detail": "User not found"}), 404

    if user.is_admin:
        admin_count = User.query.filter_by(is_admin=True).count()
        if admin_count <= 1:
            return jsonify(
                {"error": "BAD_REQUEST", "detail": "Cannot delete the last admin user"}
            ), 400

    db.session.delete(user)
    db.session.commit()
    return jsonify({"deleted": True}), 200
