"""Contract-exact JSON encoding (API_SURFACE.md § Response Envelope).

Two requirements cannot be met by `json.dumps`:

* Monetary values are `DECIMAL(10,2)` and must reach the wire as fixed
  two-decimal JSON *numbers* — `45.50`, not `45.5` and not `"45.50"`.
* Timestamps are ISO-8601 UTC with a `Z` suffix and no fractional seconds.

`json` has no `Decimal` support and its float repr drops the trailing zero, and
both the C and pure-Python encoders bypass `float.__repr__` for subclasses, so
there is no clean hook. The API emits a small, closed set of value types, so
this module walks them directly and delegates string escaping to the stdlib.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

from flask.json.provider import JSONProvider


def format_timestamp(value: datetime) -> str:
    """Render a datetime as `YYYY-MM-DDTHH:MM:SSZ`.

    Naive datetimes are stored as UTC by convention (see app.utils.dates.utc_now),
    so they are suffixed directly; aware ones are converted first.
    """
    if value.tzinfo is not None:
        value = value.astimezone(timezone.utc).replace(tzinfo=None)
    return f"{value.replace(microsecond=0).isoformat()}Z"


def encode_json(value: Any) -> str:
    """Serialise *value* to a JSON string using the contract's wire formats."""
    if isinstance(value, Mapping):
        items = ",".join(
            f"{json.dumps(str(key), ensure_ascii=False)}:{encode_json(item)}"
            for key, item in value.items()
        )
        return "{" + items + "}"
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return "[" + ",".join(encode_json(item) for item in value) + "]"
    return _encode_scalar(value)


def _encode_scalar(value: Any) -> str:
    """Serialise one leaf value.

    `datetime` is tested before `date` because a datetime is also a date.
    """
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, Decimal):
        return f"{value:.2f}"
    if isinstance(value, datetime):
        return json.dumps(format_timestamp(value))
    if isinstance(value, date):
        return json.dumps(value.isoformat())
    if isinstance(value, str):
        # ensure_ascii=False keeps non-ASCII literal, so a currency of "€"
        # reaches the wire as "€" exactly as API_SURFACE.md § 3.1 shows it.
        # JSON is UTF-8 by default (RFC 8259), so no charset is needed.
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, (int, float)):
        return json.dumps(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


class ContractJSONProvider(JSONProvider):
    """Flask JSON provider backed by :func:`encode_json`."""

    def dumps(self, obj: Any, **kwargs: Any) -> str:
        """Serialise *obj*; keyword arguments are accepted for interface parity."""
        return encode_json(obj)

    def loads(self, s: str | bytes, **kwargs: Any) -> Any:
        """Parse *s* with the stdlib decoder."""
        return json.loads(s, **kwargs)
