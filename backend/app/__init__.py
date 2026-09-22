"""Flask application factory for Venn Manager.

Creates and configures the Flask app, registers extensions (SQLAlchemy, Migrate,
Login, CORS), seeds the default admin on first run, and registers all route blueprints.
"""

import os
from pathlib import Path

from flask import Flask
from flask_cors import CORS
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

from config import config_by_name

db: SQLAlchemy = SQLAlchemy()
migrate: Migrate = Migrate()
login_manager: LoginManager = LoginManager()


def create_app(config_name: str | None = None) -> Flask:
    """Create and configure the Flask application.

    Args:
        config_name: One of 'development', 'production', 'testing'.
                     Defaults to FLASK_ENV env var or 'development'.

    Returns:
        Configured Flask application instance.
    """
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "development")

    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])

    _init_extensions(app)
    _register_blueprints(app)
    _register_error_handlers(app)
    _configure_login_manager(app)

    with app.app_context():
        _seed_default_admin(app)
        _ensure_settings_singleton()

    return app


def _init_extensions(app: Flask) -> None:
    """Initialize Flask extensions with the app instance."""
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    CORS(app, supports_credentials=True)


def _register_blueprints(app: Flask) -> None:
    """Register all API route blueprints."""
    from app.routes.auth import auth_bp
    from app.routes.records import records_bp
    from app.routes.concepts import concepts_bp
    from app.routes.budget import budget_bp
    from app.routes.history import history_bp
    from app.routes.projections import projections_bp
    from app.routes.month import month_bp
    from app.routes.settings import settings_bp
    from app.routes.users import users_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(records_bp, url_prefix="/api/records")
    app.register_blueprint(concepts_bp, url_prefix="/api/concepts")
    app.register_blueprint(budget_bp, url_prefix="/api/budget")
    app.register_blueprint(history_bp, url_prefix="/api/history")
    app.register_blueprint(projections_bp, url_prefix="/api/projections")
    app.register_blueprint(month_bp, url_prefix="/api/month")
    app.register_blueprint(settings_bp, url_prefix="/api/settings")
    app.register_blueprint(users_bp, url_prefix="/api/users")


def _register_error_handlers(app: Flask) -> None:
    """Register global error handlers returning the contract error shape."""
    from app.middleware.errors import register_error_handlers
    register_error_handlers(app)


def _configure_login_manager(app: Flask) -> None:
    """Configure Flask-Login session behavior."""
    login_manager.login_view = None  # We handle auth ourselves

    @login_manager.user_loader
    def load_user(user_id: str) -> object:
        from app.models.user import User
        return db.session.get(User, int(user_id))


def _seed_default_admin(app: Flask) -> None:
    """Seed the default administrator account on first run.

    Creates the admin user from environment variables with must_change_password=True.
    Skips if any user already exists (idempotent).
    Skips silently if tables don't exist yet (pre-migration state).
    """
    from app.models.user import User

    from sqlalchemy import inspect
    inspector = inspect(db.engine)
    if "users" not in inspector.get_table_names():
        return

    if User.query.first() is not None:
        return

    from werkzeug.security import generate_password_hash

    admin = User(
        username=app.config["DEFAULT_ADMIN_USERNAME"],
        real_name="Administrator",
        password_hash=generate_password_hash(app.config["DEFAULT_ADMIN_PASSWORD"]),
        is_admin=True,
        must_change_password=True,
    )
    db.session.add(admin)
    db.session.commit()


def _ensure_settings_singleton() -> None:
    """Ensure the Settings table has exactly one row with default currency.

    Skips silently if tables don't exist yet (pre-migration state).
    """
    from app.models.settings import Settings

    from sqlalchemy import inspect
    inspector = inspect(db.engine)
    if "settings" not in inspector.get_table_names():
        return

    if Settings.query.first() is None:
        settings = Settings(currency="$")
        db.session.add(settings)
        db.session.commit()
