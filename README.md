# Venn Manager

Shared-wallet finance manager for trusted groups (couples, roommates). Single shared ledger with budgeting and projection features.

## Stack

- **Backend:** Python 3.11+, Flask, SQLAlchemy, Flask-Migrate, Flask-Login
- **Frontend:** Preact, Vite, TypeScript, Tailwind CSS v4
- **Database:** SQLite (dev), PostgreSQL-compatible (prod)

## Quick Start

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Edit with your values
flask db upgrade       # Apply migrations + seed admin
flask --app app run    # http://localhost:5000
```

### Frontend

```bash
cd frontend
npm install
npm run dev            # http://localhost:5173
```

### Default Admin

On first run, a default admin is seeded from `.env` values (`DEFAULT_ADMIN_USERNAME` / `DEFAULT_ADMIN_PASSWORD`). The admin must change their password on first login.

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Flask session secret (≥32 bytes, random) | — |
| `DATABASE_URL` | SQLAlchemy connection string | `sqlite:///venn_manager.db` |
| `FLASK_ENV` | `development` or `production` | `development` |
| `DEFAULT_ADMIN_USERNAME` | First-run admin username | `admin` |
| `DEFAULT_ADMIN_PASSWORD` | First-run admin password | `admin` |

## Testing

```bash
# Backend
cd backend
pytest --cov=app --cov-fail-under=90

# Frontend
cd frontend
npm test
```

## Contracts

- `CONTRACTS/FRONTEND.md` — frontend behavior specification
- `CONTRACTS/BACKEND.md` — API, data models, business logic specification
