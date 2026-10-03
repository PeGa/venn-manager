# Venn Manager

Shared-wallet finance manager for trusted groups (couples, roommates). A single
shared ledger with budgeting and projection — not a debt tracker, not a
multi-currency converter, not a general accounting tool.

## Stack

| Layer    | Technology                                                            |
|----------|-----------------------------------------------------------------------|
| Backend  | Python 3.11+, Flask, SQLAlchemy, Flask-Migrate, Flask-Login           |
| Frontend | Preact, Vite, TypeScript (strict), Tailwind CSS v4, TanStack Query    |
| Database | SQLite (development), PostgreSQL-compatible (production)              |
| Desktop  | Electron (future phase, not started)                                  |

## Quick start

Two terminals.

```bash
# 1. Backend — http://127.0.0.1:5000
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
#    then set SECRET_KEY:  python -c "import secrets; print(secrets.token_hex(32))"
flask --app app db upgrade    # creates the schema and seeds the first admin
flask --app app run

# 2. Frontend — http://localhost:5173
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 and sign in as `admin` / `admin` (or your
`DEFAULT_ADMIN_*` values). That first session is restricted to the password form
until the password is changed.

The dev server proxies `/api` to the backend, so the browser sees a single origin
and the session cookie can stay `SameSite=Lax`. No CORS setup is needed.

## Environment variables

Read from the environment or from `backend/.env`. The file never overrides a
variable that is already exported.

| Variable                 | Required | Default                     | Purpose                                 |
|--------------------------|----------|-----------------------------|-----------------------------------------|
| `SECRET_KEY`             | yes      | —                           | Session signing key, ≥32 bytes          |
| `DATABASE_URL`           | no       | `sqlite:///venn_manager.db` | SQLAlchemy connection string            |
| `FLASK_ENV`              | no       | `development`               | `production` enables the Secure cookie  |
| `DEFAULT_ADMIN_USERNAME` | no       | `admin`                     | Seeded admin username                   |
| `DEFAULT_ADMIN_PASSWORD` | no       | `admin`                     | Seeded admin password                   |

`create_app` refuses to start without a valid `SECRET_KEY`. Nothing is hardcoded
and nothing is committed: `.env` is gitignored.

## Testing and quality gates

```bash
# Backend — from backend/, with the venv active
pytest                              # 342 tests, fails below 90% coverage
black --check app tests migrations
isort --check-only app tests
flake8 app tests migrations
mypy                                # --strict
flask --app app db check            # fails if models drifted from migrations

# Frontend — from frontend/
npm test                            # 147 tests
npm run coverage                    # thresholds on utils, api, hooks, l10n
npm run typecheck                   # tsc --noEmit, strict
npm run build                       # type-check plus a production bundle
```

Coverage targets are AGENTS.md § TDD: 90% backend, 70% frontend logic. Current
state: **98% backend**, **95–100%** across the frontend logic directories.

## Documentation

| Path                                       | Contents                                       |
|--------------------------------------------|------------------------------------------------|
| `CONTRACTS/FRONTEND.md`                    | Phase 1: frontend behaviour                    |
| `CONTRACTS/API_SURFACE.md`                 | Phase 2: endpoints, shapes, error codes        |
| `CONTRACTS/BACKEND.md`                     | Phase 3: domain rules, projections, seeding    |
| `docs/backend/README.md`                   | Backend setup, layout, design notes            |
| `docs/backend/CONTRACT_NOTES.md`           | Contract gaps and how they were resolved       |
| `docs/frontend/README.md`                  | Frontend setup, layout, design notes           |
| `AGENTS.md`                                | Rules for any agent working on this repository |

The contracts are the source of truth. Where code and contract disagree, the
contract wins. Where the contract is silent or self-contradictory, the decision
is recorded in `docs/backend/CONTRACT_NOTES.md` with a proposed amendment rather
than resolved silently.

## Layout

```
venn-manager/
├── backend/
│   ├── app/
│   │   ├── models/       one module per table
│   │   ├── routes/       HTTP adapters: parse, validate, status codes
│   │   ├── services/     business logic; no Flask imports
│   │   ├── middleware/   envelope, error mapping, auth gates
│   │   └── utils/        framework-free validation, dates, JSON, pagination
│   ├── migrations/       Alembic; the initial migration also seeds
│   ├── tests/            mirrors app/
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/{api,components,hooks,l10n,styles,types,utils}/
│   ├── tests/
│   └── package.json
├── CONTRACTS/
├── docs/{backend,frontend}/
└── AGENTS.md
```

## API surface

23 endpoints under `/api/v1`, all returning the same envelope:

```json
{ "data": null, "error": { "code": "ERROR_CODE", "message": "…" }, "meta": null }
```

| Group          | Endpoints                                                          |
|----------------|--------------------------------------------------------------------|
| auth           | login, logout, session, password                                   |
| current-month  | state, switch                                                      |
| settings       | get, patch                                                         |
| users (admin)  | list, create, update, delete                                       |
| concepts       | list, create, rename, delete, bulk delete                          |
| records        | list, create, update, delete, bulk delete                          |
| projections    | month figures                                                      |

Auth is session-cookie based. There are no tokens, no API keys and no
registration.
