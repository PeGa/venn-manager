"""Tests for settings routes.

Covers global currency, per-user language/theme, grapheme validation.
"""

from app import db
from app.models.settings import Settings


class TestGetSettings:
    """GET /api/settings tests."""

    def test_get_settings_returns_shape(self, auth_client):
        resp = auth_client.get("/api/settings")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "currency" in data
        assert "language" in data
        assert "theme" in data


class TestSetCurrency:
    """PUT /api/settings/currency tests."""

    def test_set_currency_single_char(self, auth_client):
        resp = auth_client.put("/api/settings/currency", json={"currency": "€"})
        assert resp.status_code == 200
        assert resp.get_json()["currency"] == "€"

    def test_set_currency_emoji(self, auth_client):
        resp = auth_client.put("/api/settings/currency", json={"currency": "💰"})
        assert resp.status_code == 200

    def test_set_currency_multi_char_rejected(self, auth_client):
        resp = auth_client.put("/api/settings/currency", json={"currency": "USD"})
        assert resp.status_code == 400

    def test_set_currency_empty_rejected(self, auth_client):
        resp = auth_client.put("/api/settings/currency", json={"currency": ""})
        assert resp.status_code == 400


class TestSetLanguage:
    """PUT /api/settings/language tests."""

    def test_set_language(self, auth_client):
        resp = auth_client.put("/api/settings/language", json={"language": "es"})
        assert resp.status_code == 200
        assert resp.get_json()["language"] == "es"


class TestSetTheme:
    """PUT /api/settings/theme tests."""

    def test_set_theme_valid(self, auth_client):
        for theme in ["light", "dark", "system"]:
            resp = auth_client.put("/api/settings/theme", json={"theme": theme})
            assert resp.status_code == 200

    def test_set_theme_invalid(self, auth_client):
        resp = auth_client.put("/api/settings/theme", json={"theme": "neon"})
        assert resp.status_code == 400
