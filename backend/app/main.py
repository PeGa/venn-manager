"""Composition root. Run with `uvicorn --factory app.main:create_app`.

Wires adapters to ports: SQLAlchemy for persistence, Argon2id and random
tokens for security, FastAPI for HTTP.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from pathlib import Path

from fastapi import FastAPI, Request, Response
from sqlalchemy import Engine
from sqlalchemy.orm import sessionmaker

from app.adapters.clock import SystemClock
from app.adapters.http import routers
from app.adapters.http.errors import error_response, install_error_handlers
from app.adapters.http.frontend import mount_frontend
from app.adapters.persistence.repositories import SqlUnitOfWork, make_engine
from app.adapters.security import Argon2Hasher, SecretTokens
from app.config import Settings, load_dotenv, settings_from_env
from app.ports import Clock, PasswordHasher, TokenGenerator

JSON_METHODS = ("POST", "PATCH", "PUT")
REVISION_HEADER = "X-Ledger-Rev"

Handler = Callable[[Request], Awaitable[Response]]


def create_app(
    settings: Settings | None = None,
    *,
    engine: Engine | None = None,
    clock: Clock | None = None,
    hasher: PasswordHasher | None = None,
    tokens: TokenGenerator | None = None,
) -> FastAPI:
    """Build the API. Arguments replace the default adapters, mainly for tests."""
    if settings is None:
        load_dotenv(Path(".env"))
        settings = settings_from_env()
    app = _fastapi(settings)
    app.state.settings = settings
    app.state.sessionmaker = sessionmaker(
        engine or make_engine(settings.database_url), expire_on_commit=False
    )
    app.state.clock = clock or SystemClock()
    app.state.hasher = hasher or Argon2Hasher()
    app.state.tokens = tokens or SecretTokens()
    install_error_handlers(app)
    app.middleware("http")(_add_revision_header)
    app.middleware("http")(_require_json)
    for router in routers:
        app.include_router(router, prefix="/api/v1")
    if settings.frontend_dist is not None:
        mount_frontend(app, Path(settings.frontend_dist))
    return app


def _fastapi(settings: Settings) -> FastAPI:
    """The bare FastAPI app. Interactive docs only outside production."""
    production = settings.app_env == "production"
    return FastAPI(
        title="Venn Manager",
        openapi_url=None if production else "/api/openapi.json",
        docs_url=None if production else "/api/docs",
        redoc_url=None,
    )


async def _require_json(request: Request, call_next: Handler) -> Response:
    """Reject non-JSON writes: with SameSite=Lax this is the CSRF defence."""
    if request.method in JSON_METHODS:
        media_type = request.headers.get("content-type", "").split(";")[0]
        if media_type.strip().lower() != "application/json":
            return error_response(400, "VALIDATION", "Requests must be JSON")
    return await call_next(request)


async def _add_revision_header(request: Request, call_next: Handler) -> Response:
    """Stamp successful responses with the ledger revision (BACKEND.md § 10)."""
    response = await call_next(request)
    if response.status_code < 400:
        with request.app.state.sessionmaker() as db:
            response.headers[REVISION_HEADER] = str(
                SqlUnitOfWork(db).household.get().rev
            )
    return response
