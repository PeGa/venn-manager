"""Application factory. Run with `uvicorn --factory app.main:create_app`."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from pathlib import Path

from fastapi import FastAPI, Request, Response
from sqlalchemy import Engine, select
from sqlalchemy.orm import sessionmaker

from app.api import routers
from app.clock import Clock, SystemClock
from app.config import Settings, load_dotenv, settings_from_env
from app.db import make_engine
from app.errors import error_response, install_error_handlers
from app.models import Household

JSON_METHODS = ("POST", "PATCH", "PUT")
REVISION_HEADER = "X-Ledger-Rev"

Handler = Callable[[Request], Awaitable[Response]]


def create_app(
    settings: Settings | None = None,
    *,
    engine: Engine | None = None,
    clock: Clock | None = None,
) -> FastAPI:
    """Build the API. Arguments override the environment, mainly for tests."""
    if settings is None:
        load_dotenv(Path(".env"))
        settings = settings_from_env()
    engine = engine or make_engine(settings.database_url)
    production = settings.app_env == "production"
    app = FastAPI(
        title="Venn Manager",
        openapi_url=None if production else "/api/openapi.json",
        docs_url=None if production else "/api/docs",
        redoc_url=None,
    )
    app.state.settings = settings
    app.state.sessionmaker = sessionmaker(engine, expire_on_commit=False)
    app.state.clock = clock or SystemClock()
    install_error_handlers(app)
    app.middleware("http")(_add_revision_header)
    app.middleware("http")(_require_json)
    for router in routers:
        app.include_router(router, prefix="/api/v1")
    return app


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
            rev = db.scalar(select(Household.rev))
        if rev is not None:
            response.headers[REVISION_HEADER] = str(rev)
    return response
