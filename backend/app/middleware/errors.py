"""Global error handlers returning the contract error shape.

All errors follow: { "error": "ERROR_CODE", "detail": "Human-readable description" }
Never exposes stack traces, SQL queries, or internal paths.
"""

from flask import Flask, jsonify


def register_error_handlers(app: Flask) -> None:
    """Register error handlers on the Flask app.

    Args:
        app: The Flask application instance.
    """

    @app.errorhandler(400)
    def bad_request(e: Exception) -> tuple:
        return jsonify({"error": "BAD_REQUEST", "detail": str(e)}), 400

    @app.errorhandler(401)
    def unauthorized(e: Exception) -> tuple:
        return jsonify({"error": "UNAUTHORIZED", "detail": "Authentication required"}), 401

    @app.errorhandler(403)
    def forbidden(e: Exception) -> tuple:
        detail = str(e) if str(e) else "Insufficient permissions"
        return jsonify({"error": "FORBIDDEN", "detail": detail}), 403

    @app.errorhandler(404)
    def not_found(e: Exception) -> tuple:
        return jsonify({"error": "NOT_FOUND", "detail": "Resource not found"}), 404

    @app.errorhandler(409)
    def conflict(e: Exception) -> tuple:
        return jsonify({"error": "CONFLICT", "detail": str(e)}), 409

    @app.errorhandler(500)
    def internal_error(e: Exception) -> tuple:
        app.logger.exception("Internal server error")
        return jsonify(
            {"error": "INTERNAL_ERROR", "detail": "An unexpected error occurred"}
        ), 500
