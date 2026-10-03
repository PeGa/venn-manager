"""Request dependencies: the use-case context and the signed-in member."""

from __future__ import annotations

from collections.abc import Iterator

from fastapi import Depends, Request

from app.adapters.persistence.repositories import SqlUnitOfWork
from app.application.auth import Auth, authenticate, require_admin, require_usable
from app.config import Settings
from app.ports import Context

COOKIE_NAME = "venn_session"


def get_settings(request: Request) -> Settings:
    """The app settings."""
    settings: Settings = request.app.state.settings
    return settings


def get_ctx(request: Request) -> Iterator[Context]:
    """One unit of work per request, plus the app-wide ports."""
    state = request.app.state
    with state.sessionmaker() as db:
        yield Context(
            uow=SqlUnitOfWork(db),
            clock=state.clock,
            hasher=state.hasher,
            tokens=state.tokens,
        )


def authenticated(request: Request, ctx: Context = Depends(get_ctx)) -> Auth:
    """Any valid session, including one that must change its password."""
    return authenticate(ctx, request.cookies.get(COOKIE_NAME))


def member(auth: Auth = Depends(authenticated)) -> Auth:
    """A session allowed to use the app."""
    return require_usable(auth)


def admin(auth: Auth = Depends(member)) -> Auth:
    """A session of an admin."""
    return require_admin(auth)
