"""Environment helpers.

`python-dotenv` is deliberately not a dependency: AGENTS.md § Adding New
Dependencies forbids one when the job fits in under 20 lines, and `.env.example`
only documents the plain `KEY=value` form handled here.
"""

from __future__ import annotations

import os
from pathlib import Path

_QUOTE_PAIRS = (('"', '"'), ("'", "'"))


def load_dotenv(path: Path) -> None:
    """Load `KEY=value` lines from *path* into the process environment.

    Already-exported variables win, so a real environment always overrides the
    file. Comments, blank lines and lines without `=` are ignored.
    """
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        for opening, closing in _QUOTE_PAIRS:
            if value.startswith(opening) and value.endswith(closing):
                value = value[1:-1]
                break
        os.environ.setdefault(key, value)
