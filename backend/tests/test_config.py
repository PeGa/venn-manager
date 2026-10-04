from pathlib import Path

import pytest

from app.config import Settings, load_dotenv, settings_from_env


def test_settings_from_env_with_nothing_set_uses_defaults() -> None:
    assert settings_from_env({}) == Settings()


def test_settings_from_env_with_values_reads_them() -> None:
    settings = settings_from_env(
        {
            "DATABASE_URL": "sqlite:///x.db",
            "APP_ENV": "production",
            "DEFAULT_ADMIN_USERNAME": "root",
            "DEFAULT_ADMIN_PASSWORD": "secret-pass",
            "DEFAULT_TIMEZONE": "Europe/Madrid",
        }
    )
    assert settings.database_url == "sqlite:///x.db"
    assert settings.secure_cookies is True
    assert settings.default_admin_username == "root"
    assert settings.default_admin_password == "secret-pass"
    assert settings.default_timezone == "Europe/Madrid"


def test_settings_from_env_in_development_disables_secure_cookies() -> None:
    assert settings_from_env({}).secure_cookies is False


def test_settings_from_env_with_unknown_app_env_raises() -> None:
    with pytest.raises(ValueError, match="APP_ENV"):
        settings_from_env({"APP_ENV": "staging"})


def test_settings_from_env_with_unknown_timezone_raises() -> None:
    with pytest.raises(ValueError, match="DEFAULT_TIMEZONE"):
        settings_from_env({"DEFAULT_TIMEZONE": "Mars/Olympus"})


def test_load_dotenv_with_file_sets_missing_keys_only(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "# comment\n\nAPP_ENV=production\nDEFAULT_TIMEZONE='UTC'\nnot a pair\n",
        encoding="utf-8",
    )
    environ = {"APP_ENV": "development"}
    load_dotenv(env_file, environ)
    assert environ == {"APP_ENV": "development", "DEFAULT_TIMEZONE": "UTC"}


def test_load_dotenv_with_missing_file_does_nothing(tmp_path: Path) -> None:
    environ: dict[str, str] = {}
    load_dotenv(tmp_path / "absent.env", environ)
    assert environ == {}


def test_settings_from_env_reads_the_frontend_build() -> None:
    assert (
        settings_from_env({"FRONTEND_DIST": "/app/dist"}).frontend_dist == "/app/dist"
    )
    assert settings_from_env({"FRONTEND_DIST": ""}).frontend_dist is None
