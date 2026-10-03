"""Alembic environment. Uses the same settings and engine as the app."""

from __future__ import annotations

from logging.config import fileConfig
from pathlib import Path

from alembic import context

from app import models  # noqa: F401  (registers every table on Base.metadata)
from app.config import load_dotenv, settings_from_env
from app.db import Base, make_engine

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

load_dotenv(Path(".env"))
settings = settings_from_env()

engine = make_engine(settings.database_url)
with engine.begin() as connection:
    context.configure(
        connection=connection,
        target_metadata=Base.metadata,
        render_as_batch=True,
    )
    context.run_migrations()
engine.dispose()
