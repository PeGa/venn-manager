"""Shared test utilities."""

from __future__ import annotations

from datetime import datetime, timedelta

from fastapi.testclient import TestClient

JSON = {"Content-Type": "application/json"}
ADMIN_PASSWORD = "admin-password"


class FakeClock:
    """A clock that only moves when told to, plus one microsecond per reading.

    The tick keeps creation order deterministic without real sleeps.
    """

    def __init__(self, start: datetime) -> None:
        self.current = start

    def now(self) -> datetime:
        self.current += timedelta(microseconds=1)
        return self.current

    def set(self, moment: datetime) -> None:
        self.current = moment

    def advance(self, delta: timedelta) -> None:
        self.current += delta


def sign_in(
    client: TestClient, username: str = "admin", password: str = "admin"
) -> None:
    """Log in and, if required, set *password* again so the gate lifts."""
    response = client.post(
        "/api/v1/auth/login", json={"username": username, "password": password}
    )
    assert response.status_code == 200, response.json()
    if response.json()["mustChangePassword"]:
        changed = client.post(
            "/api/v1/auth/password",
            json={"currentPassword": password, "newPassword": ADMIN_PASSWORD},
        )
        assert changed.status_code == 204


def add_member(
    client: TestClient,
    username: str,
    *,
    is_admin: bool = False,
    password: str = "initial-pass",
) -> dict[str, object]:
    """Create a member through the API as the signed-in admin."""
    response = client.post(
        "/api/v1/members",
        json={
            "username": username,
            "realName": username.capitalize(),
            "password": password,
            "isAdmin": is_admin,
        },
    )
    assert response.status_code == 201, response.json()
    body: dict[str, object] = response.json()
    return body
