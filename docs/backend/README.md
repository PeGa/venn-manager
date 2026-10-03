# Backend

The Venn Manager API. Behavior is defined in `CONTRACTS/BACKEND.md` and `CONTRACTS/API_SURFACE.md`. This page covers setup, layout and how to change things.

## Setup

```bash
cd backend
python3 -m venv venv
venv/bin/pip install -r requirements.txt
cp .env.example .env
venv/bin/alembic upgrade head        # creates the schema and seeds the household and admin
venv/bin/uvicorn --factory app.main:create_app --reload
```

The API listens on `http://127.0.0.1:8000/api/v1`. Interactive docs are at `/api/docs` outside production.

Sign in as `admin` / `admin` (or your `DEFAULT_ADMIN_*` values). Every new account must set a password at first sign-in.

## Environment

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `sqlite:///venn_manager.db` | SQLAlchemy connection string |
| `APP_ENV` | `development` | `production` adds the `Secure` cookie flag and hides `/api/docs` |
| `DEFAULT_ADMIN_USERNAME` | `admin` | Seeded admin username |
| `DEFAULT_ADMIN_PASSWORD` | `admin` | Seeded admin password |
| `DEFAULT_TIMEZONE` | `UTC` | Seeded household time zone |

Values come from the environment or from `backend/.env`. An exported variable always wins over the file.

## Quality gates

```bash
venv/bin/pytest                      # fails below 90% coverage
venv/bin/ruff format --check .
venv/bin/ruff check .
venv/bin/mypy                        # --strict
venv/bin/pip-audit -r requirements.txt
```

`tests/adapters/test_migrations.py` fails when the models and the migrations drift apart. `tests/test_architecture.py` fails when the core imports a framework or an adapter.

## Layout

The backend is hexagonal (AGENTS.md § Hexagonal architecture).

| Path | Holds |
|---|---|
| `app/domain/` | Entities (plain dataclasses), formulas and rules. Standard library only |
| `app/ports.py` | Every interface the use cases need |
| `app/application/` | Use cases, one module per feature |
| `app/adapters/persistence/` | Tables, imperative mapping, repositories |
| `app/adapters/http/` | FastAPI routers, request and response shapes, error mapping |
| `app/adapters/security.py` | Argon2id hashing and session tokens |
| `app/main.py` | Composition root |
| `migrations/` | Alembic. The first migration also seeds |

## Common changes

**A new field on an existing record.**
1. Add it to the dataclass in `app/domain/entities.py`.
2. Add the column in `app/adapters/persistence/tables.py`.
3. Generate a migration: `venv/bin/alembic revision --autogenerate -m "..."`.
4. Expose it in the router's response shape in `app/adapters/http/`.

**A new rule or formula.** Change `app/domain/` and its tests. Nothing else should need to move.

**A new endpoint.** Add a use case in `app/application/`, a port method if it needs new data, the repository query, and a route.

## Design notes

- **Money** is integer cents everywhere. Totals use SQL `SUM`.
- **Rollover** needs no job. The current period is the month of "today" in the household time zone; everything older is History.
- **Sessions** are random tokens. The database stores only their SHA-256.
- **Activity** entries store a snapshot of names. Targets resolve at read time, so a deleted record yields a `none` target.
- **Revision**: every successful mutation bumps `household.rev` in the same transaction. Responses carry it as `X-Ledger-Rev`.
