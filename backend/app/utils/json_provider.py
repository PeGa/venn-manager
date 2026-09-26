"""Custom JSON provider that serializes Decimal with exactly two decimal places.

The contract requires: "All amounts are represented as JSON numbers with exactly
two decimal places. The value 0 is serialized as 0.00." Standard JSON serializers
drop trailing zeros (10.10 → 10.1), so we use a sentinel-based approach:
Decimal values are serialized as quoted strings ("10.10"), then post-processed
to remove the quotes, producing valid JSON numbers with forced precision.
"""

import json
import re
from decimal import Decimal

from flask.json.provider import DefaultJSONProvider

# Matches quoted strings that look like decimal numbers with exactly 2 places
_DECIMAL_PATTERN = re.compile(r'"(-?\d+\.\d{2})"')


class VennJSONProvider(DefaultJSONProvider):
    """JSON provider that formats Decimal values to exactly two decimal places."""

    def dumps(self, obj: object, **kwargs: object) -> str:
        kwargs.setdefault("default", self._default)
        result = json.dumps(obj, **kwargs)
        return _DECIMAL_PATTERN.sub(r"\1", result)

    @staticmethod
    def _default(obj: object) -> object:
        if isinstance(obj, Decimal):
            return format(obj, ".2f")
        raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")
