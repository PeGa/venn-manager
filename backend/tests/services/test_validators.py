"""Tests for input validation utilities."""

import pytest

from app.utils.validators import (
    validate_amount,
    validate_currency,
    validate_date,
    validate_flow,
    validate_month,
    validate_string,
    validate_theme,
)


class TestValidateDate:
    def test_valid_date(self):
        assert validate_date("2026-09-15") == "2026-09-15"

    def test_invalid_format(self):
        with pytest.raises(ValueError):
            validate_date("15/09/2026")

    def test_invalid_date(self):
        with pytest.raises(ValueError):
            validate_date("2026-02-30")


class TestValidateMonth:
    def test_valid_month(self):
        assert validate_month("2026-09") == "2026-09"

    def test_invalid_format(self):
        with pytest.raises(ValueError):
            validate_month("2026/09")

    def test_invalid_month_value(self):
        with pytest.raises(ValueError):
            validate_month("2026-13")


class TestValidateAmount:
    def test_valid_amount(self):
        assert validate_amount(42.50) > 0

    def test_two_decimal_places(self):
        validate_amount("10.99")

    def test_too_many_decimals(self):
        with pytest.raises(ValueError):
            validate_amount("10.999")

    def test_invalid_amount(self):
        with pytest.raises(ValueError):
            validate_amount("not a number")


class TestValidateString:
    def test_valid_string(self):
        assert validate_string("hello", 64, "name") == "hello"

    def test_strips_whitespace(self):
        assert validate_string("  hello  ", 64, "name") == "hello"

    def test_empty_rejected(self):
        with pytest.raises(ValueError):
            validate_string("", 64, "name")

    def test_too_long_rejected(self):
        with pytest.raises(ValueError):
            validate_string("x" * 65, 64, "name")


class TestValidateFlow:
    def test_valid_flows(self):
        assert validate_flow("IN") == "IN"
        assert validate_flow("OUT") == "OUT"

    def test_invalid_flow(self):
        with pytest.raises(ValueError):
            validate_flow("MAYBE")


class TestValidateTheme:
    def test_valid_themes(self):
        for t in ["light", "dark", "system"]:
            assert validate_theme(t) == t

    def test_invalid_theme(self):
        with pytest.raises(ValueError):
            validate_theme("neon")


class TestValidateCurrency:
    def test_single_char(self):
        assert validate_currency("$") == "$"

    def test_emoji(self):
        assert validate_currency("💰") == "💰"

    def test_multi_char_rejected(self):
        with pytest.raises(ValueError):
            validate_currency("USD")

    def test_empty_rejected(self):
        with pytest.raises(ValueError):
            validate_currency("")
