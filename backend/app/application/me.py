"""The signed-in member's own profile and preferences (API_SURFACE.md § 3)."""

from __future__ import annotations

from dataclasses import dataclass

from app.application.auth import Auth, SessionView, session_view
from app.application.common import commit_mutation
from app.domain.errors import DomainError
from app.ports import Context


@dataclass(frozen=True)
class ProfileChanges:
    """Fields to change. `None` means "leave as is"."""

    username: str | None = None
    real_name: str | None = None
    language: str | None = None
    theme: str | None = None


def update_me(ctx: Context, auth: Auth, changes: ProfileChanges) -> SessionView:
    """Apply *changes* to the caller. Bumps the revision; writes no activity."""
    me = auth.member
    if changes.username is not None and changes.username != me.username:
        if ctx.uow.members.by_username(changes.username) is not None:
            raise DomainError("DUPLICATE_NAME", "Username already used", "username")
        me.username = changes.username
    if changes.real_name is not None:
        me.real_name = changes.real_name
    if changes.language is not None:
        me.language = changes.language
    if changes.theme is not None:
        me.theme = changes.theme
    commit_mutation(ctx)
    return session_view(ctx, me)
