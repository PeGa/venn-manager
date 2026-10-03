"""Flask extension singletons and the shared session type.

Isolated in their own module so models, services and the app factory can import
them without creating a cycle.
"""

from __future__ import annotations

from typing import Union

from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_sqlalchemy.session import Session as FlaskSqlalchemySession
from sqlalchemy.orm import DeclarativeBase, Session
from sqlalchemy.orm.scoping import scoped_session


class Base(DeclarativeBase):
    """Declarative base for every model.

    Models subclass this rather than `db.Model`: Flask-SQLAlchemy builds
    `db.Model` dynamically, which static analysis cannot follow, while this base
    is a real class mypy can resolve. The two share one `MetaData`, so
    `db.create_all()` and Alembic autogenerate see every table.
    """


db: SQLAlchemy = SQLAlchemy(model_class=Base)
migrate: Migrate = Migrate()
login_manager: LoginManager = LoginManager()

#: What the service layer accepts as its `session` argument.
#:
#: Routes pass Flask-SQLAlchemy's scoped proxy; unit tests and the seeding
#: migration pass a plain `Session`. `scoped_session` is invariant in its type
#: argument, so the proxy has to be named with the concrete session class
#: Flask-SQLAlchemy builds rather than with `sqlalchemy.orm.Session`.
DbSession = Union[Session, scoped_session[FlaskSqlalchemySession]]
