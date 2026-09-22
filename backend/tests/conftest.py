"""Pytest fixtures for Venn Manager backend tests.

Provides app, client, and database fixtures with automatic cleanup.
All tests use in-memory SQLite for isolation.
"""

import pytest
from werkzeug.security import generate_password_hash

from app import create_app, db as _db
from app.models.user import User
from app.models.settings import Settings


@pytest.fixture(scope="session")
def app():
    """Create application for the test session."""
    app = create_app("testing")
    yield app


@pytest.fixture(autouse=True)
def db(app):
    """Create fresh database tables for each test, drop after.

    Also seeds the settings singleton that the app factory normally creates.
    """
    with app.app_context():
        _db.create_all()
        # Seed settings singleton (app factory skips when tables don't exist at init time)
        if Settings.query.first() is None:
            _db.session.add(Settings(currency="$"))
            _db.session.commit()
        yield _db
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def client(app, db):
    """Flask test client. App context is already pushed by the db fixture."""
    with app.test_client() as client:
        yield client


@pytest.fixture
def admin_user(app, db):
    """Create an admin user for testing (password: testpass)."""
    user = User(
        username="admin",
        real_name="Test Admin",
        password_hash=generate_password_hash("testpass"),
        is_admin=True,
        must_change_password=False,
    )
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def regular_user(app, db):
    """Create a regular (non-admin) user for testing (password: testpass)."""
    user = User(
        username="user",
        real_name="Test User",
        password_hash=generate_password_hash("testpass"),
        is_admin=False,
        must_change_password=False,
    )
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def auth_client(client, admin_user):
    """Test client with an authenticated admin session."""
    client.post("/api/auth/login", json={
        "username": "admin",
        "password": "testpass",
    })
    return client


@pytest.fixture
def user_client(client, regular_user):
    """Test client with an authenticated regular user session."""
    client.post("/api/auth/login", json={
        "username": "user",
        "password": "testpass",
    })
    return client
