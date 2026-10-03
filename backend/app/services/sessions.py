"""Server-side session lifecycle.

Flask signs its session cookie but stores it in the browser, so clearing the
cookie on logout is not enough: a copied cookie would still verify. AGENTS.md
§ Authentication & Session Security requires logout to invalidate the session
*server-side*, and API_SURFACE.md § User Soft-Delete requires a deleted user's
sessions to die.

The mechanism is a per-user counter held in the existing generic `settings`
table under an internal key. A cookie carries the epoch it was issued with; the
user loader rejects it when the stored counter has moved on.

`session_epoch` is internal: `GET /settings` never returns it and
`PATCH /settings` rejects it as an unknown key.
"""

from __future__ import annotations

from sqlalchemy import select

from app.extensions import DbSession
from app.models import Setting

SESSION_EPOCH_KEY = "session_epoch"


def _row(session: DbSession, user_id: int) -> Setting | None:
    return session.scalar(
        select(Setting).where(
            Setting.key == SESSION_EPOCH_KEY, Setting.user_id == user_id
        )
    )


def current_epoch(session: DbSession, user_id: int) -> int:
    """Return the user's live epoch. Users who never logged in start at 0."""
    row = _row(session, user_id)
    return int(row.value) if row is not None else 0


def bump_epoch(session: DbSession, user_id: int) -> int:
    """Invalidate every issued cookie for one user and return the new epoch.

    Flushes without committing: the caller owns the transaction boundary.
    """
    row = _row(session, user_id)
    next_epoch = (int(row.value) if row is not None else 0) + 1
    if row is None:
        session.add(
            Setting(key=SESSION_EPOCH_KEY, value=str(next_epoch), user_id=user_id)
        )
    else:
        row.value = str(next_epoch)
    session.flush()
    return next_epoch
