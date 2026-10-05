# Venn Manager

A shared-wallet finance manager for one household: a couple, roommates, any number of people sharing one ledger. Signed transactions, budgets that plan the month, and a forecast. Not a debt tracker, not a currency converter, not an accounting tool.

## Status

| Part | State |
|---|---|
| Backend | Rewritten: FastAPI, hexagonal, all 27 endpoints of `CONTRACTS/API_SURFACE.md` |
| Frontend | Rewritten: SolidJS, hexagonal, every screen of `CONTRACTS/FRONTEND.md`, web and mobile layouts, English and Spanish |
| Desktop | Electron, future phase |

## Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12+, FastAPI, Pydantic, SQLAlchemy 2, Alembic |
| Frontend | SolidJS, Vite, TypeScript (strict), Tailwind CSS v4 |
| Database | SQLite for development, PostgreSQL-compatible for production |

## Quick start

Two terminals. Node 24 and Python 3.12+.

```bash
cd backend
python3 -m venv venv
venv/bin/pip install -r requirements.txt
cp .env.example .env
venv/bin/alembic upgrade head
venv/bin/uvicorn --factory app.main:create_app --reload
```

```bash
cd frontend
npm ci
npm run dev
```

Open http://localhost:5173 and sign in as `admin` / `admin`. The first sign-in asks for a new password. The frontend proxies `/api` to the backend on port 8000.

## Docker

One container runs both services: the frontend on port 80 and the backend on port 8000. The database lives in a host directory.

```bash
sudo mkdir -p /var/lib/venn-manager
docker compose up -d --build
```

Settings are listed at the top of `docker-compose.yml`.

## Environment variables

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `DATABASE_URL` | no | `sqlite:///venn_manager.db` | SQLAlchemy connection string |
| `APP_ENV` | no | `development` | `production` enables the `Secure` cookie flag |
| `DEFAULT_ADMIN_USERNAME` | no | `admin` | Seeded admin username |
| `DEFAULT_ADMIN_PASSWORD` | no | `admin` | Seeded admin password |
| `DEFAULT_TIMEZONE` | no | `UTC` | Seeded household time zone |
| `CORS_ORIGINS` | no | — | Origins allowed to call the API from another port (Docker) |

Read from the environment or from `backend/.env`, which is gitignored.

## Testing

```bash
cd backend
venv/bin/pytest            # fails below 90% coverage
venv/bin/ruff check .
venv/bin/mypy              # --strict
```

```bash
cd frontend
npm run coverage           # fails below 70% on the logic layers
npm run typecheck
npm run lint
```

## Documentation

| Path | Contents |
|---|---|
| `CONTRACTS/FRONTEND.md` | Screens, behavior, which actions reach the backend |
| `CONTRACTS/API_SURFACE.md` | Endpoints, shapes, errors |
| `CONTRACTS/BACKEND.md` | Domain rules and every formula |
| `docs/backend/README.md` | Backend setup, layout, how to change things |
| `docs/frontend/README.md` | Frontend setup, layout, how to change things |
| `AGENTS.md` | Rules for any agent working on this repository |
