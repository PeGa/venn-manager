"""Endpoint tests for API_SURFACE.md § 3.1 (general and profile settings)."""

from __future__ import annotations

from collections.abc import Callable

import pytest
from flask.testing import FlaskClient
from sqlalchemy import select

from app.extensions import db
from app.models import Setting, User
from app.services.settings import GLOBAL_SCOPE, SETTING_SPECS, SettingSpec

PATH = "/api/v1/settings"


@pytest.fixture()
def alice(make_user: Callable[..., User]) -> User:
    return make_user("alice", real_name="Alice Doe")


@pytest.fixture()
def bob(make_user: Callable[..., User]) -> User:
    return make_user("bob", real_name="Bob Doe")


class TestGetSettings:
    def test_anonymous_returns_401(self, client: FlaskClient) -> None:
        assert client.get(PATH).status_code == 401

    def test_returns_the_documented_keys(
        self, client: FlaskClient, alice: User, login: Callable[..., None]
    ) -> None:
        login("alice")

        response = client.get(PATH)

        assert response.status_code == 200
        assert response.get_json() == {
            "data": {
                "currency": "$",
                "language": "en",
                "theme": "system",
                "last_acknowledged_month": "2025-07",
                "username": "alice",
                "real_name": "Alice Doe",
            },
            "error": None,
            "meta": None,
        }

    def test_internal_keys_are_never_returned(
        self,
        client: FlaskClient,
        alice: User,
        login: Callable[..., None],
        put_setting: Callable[..., None],
    ) -> None:
        put_setting("session_epoch", "3", alice.id)
        login("alice")

        data = client.get(PATH).get_json()["data"]

        assert "session_epoch" not in data

    def test_stored_values_are_reflected(
        self,
        client: FlaskClient,
        alice: User,
        login: Callable[..., None],
        put_setting: Callable[..., None],
    ) -> None:
        put_setting("currency", "€")
        put_setting("theme", "dark", alice.id)
        login("alice")

        data = client.get(PATH).get_json()["data"]

        assert data["currency"] == "€"
        assert data["theme"] == "dark"


class TestPatchSettings:
    def test_anonymous_returns_401(self, client: FlaskClient) -> None:
        assert client.patch(PATH, json={"theme": "dark"}).status_code == 401

    def test_updates_currency_and_returns_only_changed_keys(
        self, client: FlaskClient, alice: User, login: Callable[..., None]
    ) -> None:
        login("alice")

        response = client.patch(PATH, json={"currency": "€", "language": "es"})

        assert response.status_code == 200
        assert response.get_json() == {
            "data": {"currency": "€", "language": "es"},
            "error": None,
            "meta": None,
        }

    def test_changes_persist_across_sessions(
        self, client: FlaskClient, alice: User, login: Callable[..., None]
    ) -> None:
        """AGENTS.md: no setting may exist only in frontend or session state."""
        login("alice")
        client.patch(PATH, json={"currency": "£", "theme": "light"})
        client.post("/api/v1/auth/logout")
        login("alice")

        data = client.get(PATH).get_json()["data"]

        assert data["currency"] == "£"
        assert data["theme"] == "light"

    def test_currency_is_global_and_affects_other_users(
        self,
        client: FlaskClient,
        alice: User,
        bob: User,
        login: Callable[..., None],
    ) -> None:
        login("alice")
        client.patch(PATH, json={"currency": "¥"})
        client.post("/api/v1/auth/logout")
        login("bob")

        assert client.get(PATH).get_json()["data"]["currency"] == "¥"

    def test_language_is_per_user(
        self,
        client: FlaskClient,
        alice: User,
        bob: User,
        login: Callable[..., None],
    ) -> None:
        login("alice")
        client.patch(PATH, json={"language": "es"})
        client.post("/api/v1/auth/logout")
        login("bob")

        assert client.get(PATH).get_json()["data"]["language"] == "en"

    def test_non_admin_may_change_currency(
        self, client: FlaskClient, alice: User, login: Callable[..., None]
    ) -> None:
        """FRONTEND.md § 5.1.3: currency is deliberately open to every user."""
        login("alice")

        assert client.patch(PATH, json={"currency": "€"}).status_code == 200

    def test_admin_only_setting_blocks_non_admins(
        self,
        client: FlaskClient,
        alice: User,
        login: Callable[..., None],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # The contract table marks every documented key as non-admin today. The
        # 403 path is exercised by tightening a spec, which is what a future
        # contract amendment would do.
        monkeypatch.setitem(
            SETTING_SPECS, "currency", SettingSpec(GLOBAL_SCOPE, requires_admin=True)
        )
        login("alice")

        response = client.patch(PATH, json={"currency": "€"})

        assert response.status_code == 403
        assert response.get_json()["error"]["code"] == "FORBIDDEN"

    def test_emoji_currency_is_accepted_as_one_grapheme(
        self, client: FlaskClient, alice: User, login: Callable[..., None]
    ) -> None:
        # FRONTEND.md § 5.1.3: a multi-codepoint emoji counts as one symbol.
        family = "\U0001f468\u200d\U0001f469\u200d\U0001f467"
        login("alice")

        response = client.patch(PATH, json={"currency": family})

        assert response.status_code == 200
        assert client.get(PATH).get_json()["data"]["currency"] == family

    def test_multi_grapheme_currency_returns_422(
        self, client: FlaskClient, alice: User, login: Callable[..., None]
    ) -> None:
        login("alice")

        response = client.patch(PATH, json={"currency": "USD"})

        assert response.status_code == 422
        assert response.get_json()["error"]["code"] == "VALIDATION_ERROR"

    def test_empty_currency_returns_422(
        self, client: FlaskClient, alice: User, login: Callable[..., None]
    ) -> None:
        login("alice")

        assert client.patch(PATH, json={"currency": "  "}).status_code == 422

    def test_unknown_theme_returns_422(
        self, client: FlaskClient, alice: User, login: Callable[..., None]
    ) -> None:
        login("alice")

        assert client.patch(PATH, json={"theme": "neon"}).status_code == 422

    def test_unknown_language_returns_422(
        self, client: FlaskClient, alice: User, login: Callable[..., None]
    ) -> None:
        login("alice")

        assert client.patch(PATH, json={"language": "fr"}).status_code == 422

    def test_unknown_key_returns_422(
        self, client: FlaskClient, alice: User, login: Callable[..., None]
    ) -> None:
        login("alice")

        response = client.patch(PATH, json={"colour": "red"})

        assert response.status_code == 422

    def test_read_only_key_returns_422(
        self, client: FlaskClient, alice: User, login: Callable[..., None]
    ) -> None:
        """Only POST /current-month/switch may move the working month."""
        login("alice")

        response = client.patch(PATH, json={"last_acknowledged_month": "2025-01"})

        assert response.status_code == 422

    def test_internal_key_is_rejected(
        self, client: FlaskClient, alice: User, login: Callable[..., None]
    ) -> None:
        login("alice")

        assert client.patch(PATH, json={"session_epoch": "99"}).status_code == 422

    def test_empty_body_returns_422(
        self, client: FlaskClient, alice: User, login: Callable[..., None]
    ) -> None:
        login("alice")

        assert client.patch(PATH, json={}).status_code == 422

    def test_non_object_body_returns_422(
        self, client: FlaskClient, alice: User, login: Callable[..., None]
    ) -> None:
        login("alice")

        assert client.patch(PATH, json=["theme"]).status_code == 422

    def test_invalid_value_type_returns_422(
        self, client: FlaskClient, alice: User, login: Callable[..., None]
    ) -> None:
        login("alice")

        assert client.patch(PATH, json={"theme": 3}).status_code == 422

    def test_nothing_is_written_when_one_key_is_invalid(
        self, client: FlaskClient, alice: User, login: Callable[..., None]
    ) -> None:
        login("alice")

        assert (
            client.patch(PATH, json={"theme": "dark", "language": "fr"}).status_code
            == 422
        )
        assert db.session.scalars(select(Setting)).all() == []


class TestProfileSettings:
    def test_username_change_persists(
        self, client: FlaskClient, alice: User, login: Callable[..., None]
    ) -> None:
        login("alice")

        response = client.patch(PATH, json={"username": "alicia"})

        assert response.status_code == 200
        assert response.get_json()["data"] == {"username": "alicia"}
        assert client.get(PATH).get_json()["data"]["username"] == "alicia"

    def test_real_name_change_persists(
        self, client: FlaskClient, alice: User, login: Callable[..., None]
    ) -> None:
        login("alice")

        client.patch(PATH, json={"real_name": "Alice Smith"})

        assert client.get(PATH).get_json()["data"]["real_name"] == "Alice Smith"

    def test_taken_username_returns_409(
        self,
        client: FlaskClient,
        alice: User,
        bob: User,
        login: Callable[..., None],
    ) -> None:
        login("alice")

        response = client.patch(PATH, json={"username": "bob"})

        assert response.status_code == 409
        assert response.get_json()["error"]["code"] == "CONFLICT"

    def test_username_of_a_deleted_user_stays_reserved(
        self,
        client: FlaskClient,
        alice: User,
        make_user: Callable[..., User],
        login: Callable[..., None],
    ) -> None:
        make_user("ghost", is_deleted=True)
        login("alice")

        assert client.patch(PATH, json={"username": "ghost"}).status_code == 409

    def test_own_username_is_not_a_conflict(
        self, client: FlaskClient, alice: User, login: Callable[..., None]
    ) -> None:
        login("alice")

        assert client.patch(PATH, json={"username": "alice"}).status_code == 200

    def test_username_is_trimmed(
        self, client: FlaskClient, alice: User, login: Callable[..., None]
    ) -> None:
        login("alice")

        client.patch(PATH, json={"username": "  alicia  "})

        assert client.get(PATH).get_json()["data"]["username"] == "alicia"

    def test_overlong_username_returns_422(
        self, client: FlaskClient, alice: User, login: Callable[..., None]
    ) -> None:
        login("alice")

        assert client.patch(PATH, json={"username": "x" * 65}).status_code == 422

    def test_empty_real_name_returns_422(
        self, client: FlaskClient, alice: User, login: Callable[..., None]
    ) -> None:
        login("alice")

        assert client.patch(PATH, json={"real_name": "   "}).status_code == 422

    def test_profile_keys_are_not_stored_in_settings(
        self, client: FlaskClient, alice: User, login: Callable[..., None]
    ) -> None:
        """API_SURFACE.md § 3.1: profile keys live on the users table."""
        login("alice")
        client.patch(PATH, json={"username": "alicia", "real_name": "Alice Smith"})

        assert db.session.scalars(select(Setting)).all() == []
