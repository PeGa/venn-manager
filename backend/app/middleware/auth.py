"""Authentication and authorization decorators.

Provides login_required enforcement and must_change_password gate.
All non-auth endpoints require a valid session. Admin-only endpoints
additionally require is_admin=True.
"""

from functools import wraps
from typing import Callable

from flask import jsonify
from flask_login import current_user


def login_required(fn: Callable) -> Callable:
    """Decorator enforcing authenticated session on a route.

    Returns 401 if no valid session exists.
    Returns 403 if must_change_password is True (except for auth endpoints).
    """

    @wraps(fn)
    def wrapper(*args: object, **kwargs: object) -> object:
        if not current_user.is_authenticated:
            return jsonify({"error": "UNAUTHORIZED", "detail": "Authentication required"}), 401
        if current_user.must_change_password:
            return jsonify(
                {"error": "FORBIDDEN", "detail": "Password change required"}
            ), 403
        return fn(*args, **kwargs)

    return wrapper


def admin_required(fn: Callable) -> Callable:
    """Decorator enforcing admin role on a route.

    Must be applied after login_required. Returns 403 if user is not admin.
    """

    @wraps(fn)
    def wrapper(*args: object, **kwargs: object) -> object:
        if not current_user.is_admin:
            return jsonify(
                {"error": "FORBIDDEN", "detail": "Administrator access required"}
            ), 403
        return fn(*args, **kwargs)

    return wrapper
