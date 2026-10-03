# AGENTS.md — Venn Manager

Rules for any AI coding agent working on this project. Read this before writing a single line of code. Violations will be reverted without discussion.

---

## Project Context

Venn Manager is a shared-wallet finance manager for one household: a couple, roommates, any number of people sharing one ledger. It is **not** a debt tracker, **not** a multi-currency converter, and **not** an accounting tool. It is one ledger of signed transactions, budgets that plan the month, and a forecast.

**Stack:**

| Layer | Technology |
|---|---|
| Frontend | SolidJS, Vite, TypeScript (strict), Tailwind CSS v4 |
| Backend | Python 3.12+, FastAPI, Pydantic, SQLAlchemy 2, Alembic |
| Database | SQLite for development, PostgreSQL-compatible for production |
| Desktop | Electron (future phase) |

**Sources of truth:**

| Document | Covers |
|---|---|
| `CONTRACTS/FRONTEND.md` | Screens, behavior, interactions, which actions reach the backend |
| `CONTRACTS/API_SURFACE.md` | Endpoints, shapes, errors, validation |
| `CONTRACTS/BACKEND.md` | Domain rules and every formula |
| `frontend/src/styles/index.css` | Visual reference: the design tokens for colors, type, spacing, radii, shadows |

If code and contract disagree, the contract wins. If you believe the contract is wrong, flag it. Do not silently deviate.

---

## Principles

- **Keep it simple.** The smallest design that satisfies the contract wins. No speculative abstractions, no configuration nobody asked for.
- **Use standards.** Prefer the platform, the standard library and the de facto tool of each ecosystem over custom or niche solutions.
- **Reproducible output.** Pinned versions, committed lockfiles (`package-lock.json`, `requirements.txt`), `npm ci` and `pip install -r` only. The same commit builds the same artifact on any machine.
- **Documentation, not narration.** Explain behavior in docstrings, contracts and `docs/`. Code comments only state a non-obvious *why*. Never comments that retell what the code does or how it came to be.

---

## Documentation

- Every public function, class and module has a docstring or JSDoc comment explaining **what** it does and **why**.
- Formulas in code reference the BACKEND.md section they implement, e.g. `# BACKEND.md § 4.2`.
- When adding a feature, update the relevant contract **first**, then implement. Code without a contract update is incomplete.
- README.md always reflects current setup, environment variables and run commands. Stale documentation is a bug.
- `docs/` holds user documentation for backend and frontend.
- Markdown for all documentation. Tables for structured data. Language tags on every code block. Short sentences, one idea each.

---

## Test-Driven Development

### Non-Negotiable Rules

- **No production code without a failing test first.** If you write implementation before the test, delete it and start over.
- Backend tests cover every endpoint, every formula in BACKEND.md § 4–5, every validation rule, and every auth flow.
- Frontend tests cover money and date formatting, amount parsing, the selection model, local budget recomputation, activity sentences, and screen behavior for Overview, Budget, Transactions and History. Visual layout testing is optional.
- Every bug fix includes a regression test that fails before the fix.
- Coverage: **90% minimum** backend, **70% minimum** frontend logic (`src/lib`, `src/api`, `src/l10n`). Below that is a blocking issue.

### Structure

- Backend: `pytest`, `pytest-cov`, FastAPI's `TestClient` (`httpx2`).
- Frontend: `vitest`, `@solidjs/testing-library`, `jsdom`.
- Test files mirror source files: `app/services/forecast.py` → `tests/services/test_forecast.py`.
- Each test file has fixtures, happy paths, error paths and edge cases.
- Tests are deterministic. Freeze "today" explicitly; never depend on the real clock. No network calls. No reliance on execution order.
- BACKEND.md § 4.7 (worked example) is a test, verbatim.

### Naming

`test_<unit>_<scenario>_<expected_outcome>`, e.g.:

- `test_create_transaction_with_deleted_budget_returns_410`
- `test_forecast_with_spend_inside_budget_keeps_total`
- `test_upcoming_with_monthly_anchor_on_31st_clamps_to_month_end`

### Cycle

1. **Red**: a failing test that describes the behavior.
2. **Green**: the minimum code to pass.
3. **Refactor**: clean up, tests stay green.
4. **Contract check**: the behavior matches the contract, or the discrepancy is flagged.

---

## Security

This is a finance application. Security is a first-class requirement.

### Queries

- Never build SQL with string concatenation or f-strings.
- Use the SQLAlchemy ORM or bound parameters. Any `text()` needs a comment justifying it.

### Authentication and sessions

- Session cookies only. No JWT, no bearer tokens, no API keys.
- Cookie: `HttpOnly`, `SameSite=Lax`, `Secure` in production.
- Sessions live server-side (BACKEND.md § 8.5). The cookie holds a random token. The database stores only its SHA-256 hash.
- Passwords are hashed with Argon2id (`argon2-cffi`). Never MD5, SHA1 or unsalted hashes.
- The forced password change is a stored flag (BACKEND.md § 8.4), enforced server-side on every request.
- Logout deletes the session server-side.

### Request handling

- Mutating requests must be `application/json`. With `SameSite=Lax` and no CORS, that is the CSRF defense. Do not add CORS.
- Validate every input with Pydantic models: types, lengths, ranges, enums. Reject unknown fields.
- Trim strings before validating.
- Money is integer cents. Never accept or produce floats for money.
- Dates are `YYYY-MM-DD`. Time zones are validated with `zoneinfo`.
- Bulk deletes accept at most 500 ids. Pages hold at most 200 items.
- GET requests have no side effects, so rate limiting can be added later.

### Output

- Errors never echo raw input, stack traces, SQL or internal paths.
- The frontend never renders user strings as HTML. No `innerHTML` with user data.
- Never log passwords, session tokens or environment values.

### Secrets and dependencies

- All configuration comes from environment variables. `.env` is gitignored. `.env.example` documents every variable.
- Run `pip-audit` and `npm audit` before adding a dependency. No dependency with a known critical CVE.
- Pin every version. No ranges, no wildcards.

---

## Architecture Constraints

### Contract compliance

- Do not add features, endpoints, fields or behaviors that the contracts do not describe.
- Do not change contract-defined behavior without explicit approval.
- A contract gap found during implementation is documented and proposed as an amendment. Never invented silently.

### What NOT to do

- **Do not** add JWT, bearer tokens or API keys.
- **Do not** hard-delete members, budgets or transactions through the API. They are soft-deleted.
- **Do not** add trash, restore or undo.
- **Do not** add WebSockets, SSE or polling. Screens refetch when opened (FRONTEND.md § 8).
- **Do not** add scheduled jobs. Rollover is derived from the date (BACKEND.md § 3).
- **Do not** store derived values: forecasts, totals, balances, archived flags.
- **Do not** add multi-currency support, currency conversion or locale-aware number formatting.
- **Do not** turn the activity feed into an audit trail. It records what happened in human terms. No field-level history, no versioning, no diffs.
- **Do not** add email or any external communication.
- **Do not** add a "flow" field. Money direction is the sign of the amount.
- **Do not** derive a transaction's sign from its budget. The user decides.
- **Do not** introduce a frontend framework other than SolidJS.
- **Do not** add a state management library. Use Solid signals, stores and context. Server state goes through `@tanstack/solid-query`.
- **Do not** use `any` in TypeScript.

### Separation of concerns

**Backend** (`backend/app/`):

| Layer | Responsibility |
|---|---|
| `api/` | FastAPI routers. HTTP only: parse, call a service, map errors to status codes |
| `schemas/` | Pydantic request and response models |
| `services/` | Domain logic and formulas. No FastAPI imports |
| `models/` | SQLAlchemy models |
| `auth/` | Sessions, password hashing, the request dependency that resolves the member |

No SQL in routers. No HTTP in services.

**Frontend** (`frontend/src/`):

| Folder | Responsibility |
|---|---|
| `screens/` | One component per screen. Rendering only |
| `components/` | Shared UI: cards, rows, dialogs, sheets, chips |
| `api/` | Fetch client and one query/mutation module per resource |
| `lib/` | Pure functions: money, dates, parsing, selection, local budget math |
| `l10n/` | Locale files and the translation function |
| `styles/` | Tailwind entry and design tokens |

Business logic lives in `lib/`, never in components.

### Responsive behavior

One codebase. Width decides layout, pointer type decides interaction (FRONTEND.md § 2). Never fork a screen into separate mobile and desktop components; use variants.

---

## Code Style

### Python

- `ruff format` and `ruff check` (rules: E, F, I, B, UP, S). `mypy --strict` must pass.
- Type hints everywhere.
- snake_case for functions and variables, PascalCase for classes.
- Functions under 30 lines. Longer means refactor.
- f-strings for formatting.

### TypeScript

- `strict` stays on. `tsc --noEmit` must pass.
- ESLint with `eslint-plugin-solid` and `typescript-eslint`. It catches Solid reactivity mistakes such as destructured props.
- camelCase for functions and variables, PascalCase for components and types.
- `const` by default, `let` only when reassigned, never `var`.
- Named exports only.
- Semantic HTML: `<button>` for actions, `<label>` for fields, `<dialog>` for dialogs.

### Localization

- No visible string literals in components. Every string goes through the translation function with a key (FRONTEND.md § 11).
- `l10n/en.ts` defines the key set. Every other locale is typed `Record<TranslationKey, string>`, so a missing or extra key fails the build.
- Plural-dependent strings use `_one` / `_other` keys resolved with `Intl.PluralRules`.
- Month and weekday names come from `Intl.DateTimeFormat`. Numbers never use `Intl.NumberFormat`.

### File structure

```
venn-manager/
├── backend/
│   ├── app/
│   │   ├── main.py           # app factory
│   │   ├── config.py
│   │   ├── db.py
│   │   ├── api/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── models/
│   │   └── auth/
│   ├── migrations/           # Alembic
│   ├── tests/                # mirrors app/
│   ├── pyproject.toml        # tool configuration
│   ├── requirements.txt      # pinned dependencies
│   └── .env.example
├── frontend/
│   ├── src/{screens,components,api,lib,l10n,styles}/
│   ├── tests/                # mirrors src/
│   ├── index.html
│   ├── vite.config.ts
│   ├── tsconfig.json
│   └── package.json
├── CONTRACTS/
├── docs/
├── AGENTS.md
└── README.md
```

---

## Dependency Policy

### Approved

**Backend**

| Package | Purpose |
|---|---|
| `fastapi`, `uvicorn` | HTTP |
| `pydantic` | Validation (ships with FastAPI) |
| `sqlalchemy`, `alembic` | Persistence, migrations |
| `argon2-cffi` | Password hashing |
| `tzdata` | Time zone database where the OS has none (Windows, Electron) |
| `pytest`, `pytest-cov`, `httpx2` | Testing |
| `ruff`, `mypy`, `pip-audit` | Tooling |

**Frontend**

| Package | Purpose |
|---|---|
| `solid-js`, `@solidjs/router` | UI, routing |
| `@tanstack/solid-query` | Server state, caching, retries |
| `tailwindcss`, `@tailwindcss/vite` | Styling |
| `vite`, `vite-plugin-solid`, `typescript` | Build |
| `@fontsource/dm-sans`, `@fontsource/dm-mono` | Self-hosted fonts |
| `vitest`, `@vitest/coverage-v8`, `@solidjs/testing-library`, `jsdom` | Testing |
| `eslint`, `eslint-plugin-solid`, `typescript-eslint` | Linting |

Built by hand, no dependency: the History pie chart (SVG), dialogs and sheets (native `<dialog>`), long-press, money and date formatting.

### Adding a dependency

- Justify it in a comment or in the docs.
- Audit it first.
- Prefer the standard library or an approved package.
- Never add one for convenience when the job takes under 20 lines.

---

## Commits

- [Conventional Commits](https://www.conventionalcommits.org/): `<type>(<scope>): <description>`.
- Types: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `security`.
- Scopes: `backend`, `frontend`, `api`, `auth`, `contract`, `docs`, `ci`.
- Imperative mood. One logical change per commit.
- Never commit secrets, `.env` files or generated artifacts.

Examples:

- `feat(backend): compute forecast from budgets and transactions`
- `fix(frontend): keep sign when cycling the add bar category`
- `docs(contract): define upcoming occurrences for biweekly schedules`

---

## Environment

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `DATABASE_URL` | no | `sqlite:///venn_manager.db` | SQLAlchemy connection string |
| `APP_ENV` | no | `development` | `production` enables the `Secure` cookie flag |
| `DEFAULT_ADMIN_USERNAME` | no | `admin` | Seeded admin username |
| `DEFAULT_ADMIN_PASSWORD` | no | `admin` | Seeded admin password. The admin must set a password at first sign-in |
| `DEFAULT_TIMEZONE` | no | `UTC` | Seeded household time zone |

There is no signing secret: session tokens are random and stored server-side.

---

## Performance

- No N+1 queries. Use `selectinload` or joins for relationships read in loops.
- Compute totals with SQL aggregation (`SUM`, `GROUP BY`), never by loading every row.
- Indexes as listed in BACKEND.md § 2.
- Pages hold at most 200 items.
- The frontend never refetches on every render. Queries refetch on screen open and window focus only.

---

## Error Handling

### Backend

- Error body: `{ "code", "message", "field"? }` with the codes in API_SURFACE.md § 11. Success bodies are the resource itself.
- Never return `200` with an error.
- A global handler turns unhandled exceptions into `500 INTERNAL` with a generic message and logs the details server-side.
- Pydantic validation errors become `400 VALIDATION` with `field`.

### Frontend

- Every request handles loading, success and error.
- Messages are localized by error code. Never show raw codes, server messages or stack traces.
- Network failures retry up to 3 times.
- Field errors show inline next to the field.

---

## Agent Behavior

- When unsure about a requirement, check the contracts. If they do not cover it, ask. Do not guess.
- Before a change that touches several files, list them.
- Never delete or overwrite code without checking nothing else uses it.
- Fix bugs by reproducing them with a test first.
- Stay inside the task. Note refactoring opportunities; do not act on them.
- No premature optimization. Clear and correct first.
- If a task is ambiguous, stop and ask.
- Keep the model minimal. Reuse budgets, transactions and members before inventing a new entity.
