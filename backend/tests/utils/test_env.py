"""Tests for the dependency-free `.env` loader."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from app.utils.env import load_dotenv


@pytest.fixture()
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ("VENN_A", "VENN_B", "VENN_C"):
        monkeypatch.delenv(key, raising=False)


class TestLoadDotenv:
    def test_missing_file_is_a_noop(self, tmp_path: Path, clean_env: None) -> None:
        load_dotenv(tmp_path / "absent.env")

        assert os.environ.get("VENN_A") is None

    def test_reads_key_value_pairs(
        self, tmp_path: Path, clean_env: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        path = tmp_path / ".env"
        path.write_text("VENN_A=one\nVENN_B=two\n", encoding="utf-8")

        load_dotenv(path)

        assert os.environ["VENN_A"] == "one"
        assert os.environ["VENN_B"] == "two"

    def test_ignores_comments_and_blanks(
        self, tmp_path: Path, clean_env: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        path = tmp_path / ".env"
        path.write_text("# comment\n\n   \nVENN_A=one\n", encoding="utf-8")

        load_dotenv(path)

        assert os.environ["VENN_A"] == "one"

    def test_strips_surrounding_quotes_and_whitespace(
        self, tmp_path: Path, clean_env: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        path = tmp_path / ".env"
        path.write_text("VENN_A = \"quoted\" \nVENN_B='single'\n", encoding="utf-8")

        load_dotenv(path)

        assert os.environ["VENN_A"] == "quoted"
        assert os.environ["VENN_B"] == "single"

    def test_does_not_override_existing_environment(
        self, tmp_path: Path, clean_env: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("VENN_C", "from-shell")
        path = tmp_path / ".env"
        path.write_text("VENN_C=from-file\n", encoding="utf-8")

        load_dotenv(path)

        assert os.environ["VENN_C"] == "from-shell"
