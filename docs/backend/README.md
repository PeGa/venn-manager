# Backend

Venn Manager's API. Flask + SQLAlchemy + Flask-Migrate + Flask-Login, SQLite in
development and PostgreSQL-compatible in production.

The behaviour contract is `CONTRACTS/API_SURFACE.md` (ports) and
`CONTRACTS/BACKEND.md` (domain rules). This document covers setup, layout and
operations. Decisions the contracts left open are recorded in
[CONTRACT_NOTES.md](CONTRACT_NOTES.md).

## Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # then set SECRET_KEY
flask --app app db upgrade # creates the schema and seeds the first admin
flask --app app run        # http://localhost:5000
```

`SECRET_KEY` has no default and no fallback. `create_app` refuses to start
without at least 32 bytes. Generate one with:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

The first login is `admin` / `admin` (or your `DEFAULT_ADMIN_*` values). That
session is restricted to `POST /api/v1/auth/password` until the password is
changed.

## Environment

| Variable                 | Required | Default                   | Purpose                              |
|--------------------------|----------|---------------------------|--------------------------------------|
| `SECRET_KEY`             | yes      | —                         | Session signing key, ≥32 bytes       |
| `DATABASE_URL`           | no       | `sqlite:///venn_manager.db` | SQLAlchemy connection string       |
| `FLASK_ENV`              | no       | `development`             | `production` enables the Secure cookie |
| `DEFAULT_ADMIN_USERNAME` | no       | `admin`                   | Seeded admin username                |
| `DEFAULT_ADMIN_PASSWORD` | no       | `admin`                   | Seeded admin password                |

`.env` is loaded by `app/utils/env.py`, which never overrides a variable that is
already exported. It is gitignored.

## Commands

| Command                                   | Purpose                              |
|-------------------------------------------|--------------------------------------|
| `pytest`                                  | Test suite; fails below 90% coverage |
| `pytest --no-cov`                         | Faster run while iterating           |
| `black app tests migrations`              | Format                               |
| `isort app tests`                         | Import order                         |
| `flake8 app tests migrations`             | Lint                                 |
| `mypy`                                    | Type check (`--strict`)              |
| `flask --app app db migrate -m "..."`     | Autogenerate a migration             |
| `flask --app app db upgrade`              | Apply migrations                     |
| `flask --app app db check`                | Fail if models drifted from migrations |
| `pip-audit -r requirements.txt`           | Known-CVE scan                       |

Configuration for all of these lives in `setup.cfg`.

## Layout

```
app/
├── __init__.py        # create_app: config, JSON provider, extensions, blueprints
├── config.py          # environment → config dict; SECRET_KEY policy
├── extensions.py      # db / migrate / login_manager, the declarative Base, DbSession
├── models/            # one module per table; persistence only
├── routes/            # HTTP adapters: parse, validate, status codes
├── services/          # business logic; no Flask imports
├── middleware/        # envelope, error mapping, auth gates, request parsing
└── utils/             # framework-free helpers: validation, dates, JSON, pagination
```

The split follows API_SURFACE.md § Design principle. `services/` and `utils/`
never import Flask; `middleware/` is the only layer that knows an HTTP status
code, and `routes/` is the only layer that touches `flask.request`.

## Design notes

**Money.** Amounts are `DECIMAL(10,2)` and stay `Decimal` from the database to
the wire. No float arithmetic anywhere. `app/utils/json.py` serialises `Decimal`
as a fixed two-place JSON *number*, because `json.dumps` cannot express `45.50`.

**Timestamps.** Stored naive and UTC (SQLite cannot persist offsets), rendered
with a `Z` suffix by the same encoder.

**Sessions.** Flask signs its session cookie but stores it in the browser, so
clearing the cookie is not invalidation. Each user has an internal
`session_epoch` counter in the `settings` table; a cookie carries the epoch it
was issued with and the user loader rejects a mismatch. Logout, a password
change and an admin-initiated password reset all bump it. See
[CONTRACT_NOTES.md](CONTRACT_NOTES.md#2-server-side-session-invalidation).

**Soft delete.** Everything is soft-deleted. A record's `is_deleted` only ever
describes that record. Visibility of records whose *concept* was deleted is
derived per query — hidden in the working month, kept and flagged in history —
so deleting a concept never cascades and never rewrites the past.

**Projections.** Computed per request from two grouped SQL queries; nothing is
cached or stored. The formula itself is a pure function
(`services/projections.compute_projections`) that knows nothing about Flask or
SQL, which is what makes it directly unit-testable.

**N+1.** Record and concept lists resolve their concept and user with explicit
joins in a single query rather than through lazy relationships.

## Seeding

`flask db upgrade` runs the initial migration, which creates the schema and then
calls `app.services.seed.seed_initial_data`: one admin, four global settings,
zero concepts. It is idempotent — it no-ops when any user already exists — and
it flushes rather than commits, because Alembic owns the transaction.
