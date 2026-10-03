"""Wire-format tests for the contract JSON encoder."""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from app.utils.json import encode_json


class TestEncodeJson:
    def test_decimal_keeps_two_places(self) -> None:
        assert encode_json(Decimal("45.5")) == "45.50"
        assert encode_json(Decimal("0")) == "0.00"
        assert encode_json(Decimal("-1750")) == "-1750.00"

    def test_naive_datetime_is_zulu(self) -> None:
        assert encode_json(datetime(2025, 7, 15, 10, 30)) == '"2025-07-15T10:30:00Z"'

    def test_aware_datetime_is_converted_to_utc_zulu(self) -> None:
        value = datetime(2025, 7, 15, 12, 30, tzinfo=timezone.utc)

        assert encode_json(value) == '"2025-07-15T12:30:00Z"'

    def test_date_is_iso(self) -> None:
        assert encode_json(date(2025, 7, 15)) == '"2025-07-15"'

    def test_scalars(self) -> None:
        assert encode_json(None) == "null"
        assert encode_json(True) == "true"
        assert encode_json(False) == "false"
        assert encode_json(7) == "7"
        assert encode_json("a") == '"a"'

    def test_string_escaping_delegates_to_stdlib(self) -> None:
        value = 'quote" back\\ slash\n newline <tag> é'

        assert encode_json(value) == json.dumps(value, ensure_ascii=False)

    def test_record_shape_is_emitted_verbatim(self) -> None:
        payload = {
            "data": [
                {
                    "id": 1,
                    "amount": Decimal("45.50"),
                    "date": date(2025, 7, 15),
                    "concept_is_deleted": False,
                    "note": None,
                }
            ],
            "error": None,
            "meta": None,
        }

        assert encode_json(payload) == (
            '{"data":[{"id":1,"amount":45.50,"date":"2025-07-15",'
            '"concept_is_deleted":false,"note":null}],"error":null,"meta":null}'
        )

    def test_lists_and_tuples(self) -> None:
        assert encode_json([Decimal("1"), (2, 3)]) == "[1.00,[2,3]]"

    def test_unsupported_type_raises(self) -> None:
        with pytest.raises(TypeError):
            encode_json(object())
