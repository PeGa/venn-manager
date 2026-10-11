# Venn Manager

**English** · [Español](README.es.md)

A shared ledger for the people in the overlap: couples, roommates, families. Budgets plan the month, transactions log what moves, and a forecast tells you what you'll really have when the month ends.

Venn Manager is self-hosted. It runs in one container on your own machine, keeps its data in one SQLite file, and talks to nothing else.

## What it does

- **One ledger for the whole household.** Every member signs in with their own account and sees the same money. Any member can add transactions and change budgets; admins manage accounts.
- **A month-end forecast you can trust.** The Overview shows how much money the household will have when the month ends, counting every budget. An **Explain** button lists every transaction and every budget still to move, so you can check the sum yourself.
- **Budgets that plan the month.** Each concept (Rent, Groceries, Paycheck…) has a signed amount: negative for money going out, positive for money coming in. Give a budget a due date (once, weekly, every two weeks, monthly) and it shows up under **Coming up** until it's paid.
- **Goals.** Mark a budget as a goal to track savings on their own screen.
- **Fast logging.** Type an amount, pick a category, done. Select several transactions with the mouse, or long-press on a phone.
- **History.** Past months are read-only. Search them, filter by member or category, and see where the money went in a pie chart.
- **Balance.** The household's balance and this month's money in and out. Optionally, what each member brings in.
- **Activity feed.** "Alex added −$84.12 to Groceries." Click an entry to jump to what changed.
- **Months roll over on their own.** No end-of-month routine: last month moves to History and its leftover becomes this month's starting cash.
- **Made for every screen.** Wide and narrow layouts, mouse and touch, light and dark themes, English and Spanish.

Not a debt tracker, not a currency converter, not an accounting tool. The currency sign is a label you choose; amounts are never converted.

## How the numbers work

Every transaction is signed as you type it: `-84.12` is money out, `2240` is money in. Each budget plans one concept for the month.

```text
Forecast = cash at the start of the month
         + what the budgets still expect to move
         + what has already moved this month
```

Money moved within a budget doesn't change the forecast; it was already planned. Money moved beyond a budget replaces the plan. Example: you planned −$10 for groceries and spent −$30, so the forecast now counts −$30.

## Run it with Docker

You need Docker with the Compose plugin.

```bash
git clone https://github.com/PeGa/venn-manager.git
cd venn-manager
sudo mkdir -p /var/lib/venn-manager
docker compose up -d --build
```

Open `http://<your-server>:8080` and sign in as `admin` / `admin`. You'll be asked to choose a new password right away. Then, in **Settings**:

1. Set the household name, time zone and currency sign.
2. Enter the opening balance: what the household has before it starts using Venn Manager.
3. Add budget concepts, then set their amounts in **Budget**.
4. Invite the other members.

### Configuration

Set these in your environment or in a `.env` file next to `docker-compose.yml`.

| Variable | Default | What it does |
|---|---|---|
| `VENN_PORT` | `8080` | Port the app listens on |
| `VENN_DATA_DIR` | `/var/lib/venn-manager` | Folder that holds the database, `venn_manager.db` |
| `APP_ENV` | `development` | Set to `production` when the app is served over HTTPS, to protect the session cookie |
| `DEFAULT_ADMIN_USERNAME` | `admin` | First admin's username, used only on the first start |
| `DEFAULT_ADMIN_PASSWORD` | `admin` | First admin's password, used only on the first start |
| `DEFAULT_TIMEZONE` | `UTC` | Household time zone on the first start; it decides when months begin and end |

To reach it from outside your home network, put it behind a reverse proxy with HTTPS (Caddy, nginx, Traefik…) and set `APP_ENV=production`.

### Back up

Everything lives in one file. Stop the app, copy the file, start it again:

```bash
docker compose stop
cp /var/lib/venn-manager/venn_manager.db ~/venn_manager-$(date +%F).db
docker compose start
```

### Update

```bash
git pull
docker compose up -d --build
```

Database migrations run on their own when the container starts. Back up first.

## Development

Requires Python 3.12+ and Node 24. Use two terminals.

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

Open http://localhost:5173. The dev server forwards `/api` to the backend on port 8000. Local settings live in `backend/.env`; [`docs/backend/README.md`](docs/backend/README.md) lists them all.

### Checks

```bash
cd backend
venv/bin/pytest
venv/bin/ruff check .
venv/bin/mypy
```

```bash
cd frontend
npm run coverage
npm run typecheck
npm run lint
```

### Built with

| Part | Technology |
|---|---|
| Backend | Python, FastAPI, SQLAlchemy, Alembic, SQLite |
| Frontend | SolidJS, TypeScript, Vite, Tailwind CSS |
| Container | nginx serving the frontend and proxying the API, in one image |

### Where to look

Behavior is written down before it's built, in three contracts:

| Document | Covers |
|---|---|
| [`CONTRACTS/FRONTEND.md`](CONTRACTS/FRONTEND.md) | Every screen and interaction |
| [`CONTRACTS/API_SURFACE.md`](CONTRACTS/API_SURFACE.md) | Every endpoint, shape and error |
| [`CONTRACTS/BACKEND.md`](CONTRACTS/BACKEND.md) | Domain rules and every formula |
| [`docs/backend/README.md`](docs/backend/README.md), [`docs/frontend/README.md`](docs/frontend/README.md) | Code layout and how to change things |
| [`AGENTS.md`](AGENTS.md) | Coding rules for contributors, human or not |

Changes start with the contract, then a failing test, then the code.

## Roadmap

- A desktop app (Electron).

## License

Copyright (C) 2026 PeGa!

Venn Manager is free software under the [GNU Affero General Public License v3.0](LICENSE) or any later version. All earlier versions in this repository's history are also available under AGPL-3.0-or-later.

| You may | You must |
|---|---|
| Use it, self-host it, study it, change it | Keep the copyright and license notices |
| Share it, modified or not | Share your source under the same license |
| Run a modified version as a service for others | Offer its source to the people who use it over the network |
