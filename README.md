# Venn Manager

A shared-wallet finance manager for one household: a couple, roommates, any number of people sharing one ledger. Signed transactions, budgets that plan the month, and a forecast. Not a debt tracker, not a currency converter, not an accounting tool.

## Status

| Part | State |
|---|---|
| Backend | Rewritten: FastAPI, hexagonal, all 27 endpoints of `CONTRACTS/API_SURFACE.md` |
| Frontend | Being rebuilt in SolidJS. The code in `frontend/` is the previous Preact app and is obsolete |
| Desktop | Electron, future phase |

## Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12+, FastAPI, Pydantic, SQLAlchemy 2, Alembic |
| Frontend | SolidJS, Vite, TypeScript (strict), Tailwind CSS v4 |
| Database | SQLite for development, PostgreSQL-compatible for production |

## Quick start (backend)

```bash
cd backend
python3 -m venv venv
venv/bin/pip install -r requirements.txt
cp .env.example .env
venv/bin/alembic upgrade head
venv/bin/uvicorn --factory app.main:create_app --reload
```

The API runs at `http://127.0.0.1:8000/api/v1`. Sign in as `admin` / `admin`; the first sign-in asks for a new password.

## Environment variables

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `DATABASE_URL` | no | `sqlite:///venn_manager.db` | SQLAlchemy connection string |
| `APP_ENV` | no | `development` | `production` enables the `Secure` cookie flag |
| `DEFAULT_ADMIN_USERNAME` | no | `admin` | Seeded admin username |
| `DEFAULT_ADMIN_PASSWORD` | no | `admin` | Seeded admin password |
| `DEFAULT_TIMEZONE` | no | `UTC` | Seeded household time zone |

Read from the environment or from `backend/.env`, which is gitignored.

## Testing (backend)

```bash
cd backend
venv/bin/pytest            # fails below 90% coverage
venv/bin/ruff check .
venv/bin/mypy              # --strict
```

## Documentation

| Path | Contents |
|---|---|
| `CONTRACTS/FRONTEND.md` | Screens, behavior, which actions reach the backend |
| `CONTRACTS/API_SURFACE.md` | Endpoints, shapes, errors |
| `CONTRACTS/BACKEND.md` | Domain rules and every formula |
| `docs/backend/README.md` | Backend setup, layout, how to change things |
| `AGENTS.md` | Rules for any agent working on this repository |
