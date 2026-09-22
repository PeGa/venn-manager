"""Application configuration loaded from environment variables.

Provides a Config base class and environment-specific subclasses.
All secrets and connection strings come from env vars — never hardcoded.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the backend directory
load_dotenv(Path(__file__).resolve().parent / ".env")


class Config:
    """Base configuration. Values sourced from environment variables."""

    SECRET_KEY: str = os.environ.get("SECRET_KEY", "dev-fallback-key-change-me")
    SQLALCHEMY_DATABASE_URI: str = os.environ.get(
        "DATABASE_URL", "sqlite:///venn_manager.db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    FLASK_ENV: str = os.environ.get("FLASK_ENV", "development")
    DEFAULT_ADMIN_USERNAME: str = os.environ.get("DEFAULT_ADMIN_USERNAME", "admin")
    DEFAULT_ADMIN_PASSWORD: str = os.environ.get("DEFAULT_ADMIN_PASSWORD", "admin")
    SESSION_COOKIE_HTTPONLY: bool = True
    SESSION_COOKIE_SAMESITE: str = "Lax"
    SESSION_COOKIE_SECURE: bool = os.environ.get("FLASK_ENV", "development") == "production"


class DevelopmentConfig(Config):
    """Development configuration. Relaxed cookie security for localhost."""

    DEBUG: bool = True
    SESSION_COOKIE_SECURE: bool = False


class ProductionConfig(Config):
    """Production configuration. Strict cookie security."""

    DEBUG: bool = False
    SESSION_COOKIE_SECURE: bool = True


class TestingConfig(Config):
    """Testing configuration. In-memory SQLite, no persistent state."""

    TESTING: bool = True
    SQLALCHEMY_DATABASE_URI: str = "sqlite:///:memory:"
    WTF_CSRF_ENABLED: bool = False
    SESSION_COOKIE_SECURE: bool = False


config_by_name: dict[str, type[Config]] = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}
