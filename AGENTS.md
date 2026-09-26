# AGENTS.md — Venn Manager

This file defines the rules, constraints, and expectations for any AI coding agent working on this project. Read this before writing a single line of code. Violations will be reverted without discussion.

---

## Project Context

Venn Manager is a shared-wallet finance manager for trusted groups (couples, roommates). It is **not** a debt tracker, **not** a multi-currency converter, and **not** a general-purpose accounting tool. It is a single shared ledger with budgeting and projection features.

**Stack:**
- Backend: Python 3.11+, Flask, SQLAlchemy, Flask-Migrate, Flask-Login
- Frontend: Preact, Vite, TypeScript, Tailwind CSS v4
- Desktop: Electron (future phase)
- Database: SQLite for development, PostgreSQL-compatible for production

**Contracts:**
- `CONTRACTS/FRONTEND.md` — Phase 1: frontend behavior
- `CONTRACTS/API_SURFACE.md` — Phase 2: API ports (endpoints, request/response shapes, envelope, error codes, reference schema)
- `CONTRACTS/BACKEND.md` — Phase 3: business logic and domain rules (soft delete, projections, month switch, seeding)

These contracts are the source of truth. If code and contract disagree, the contract wins. If you believe the contract is wrong, flag it. Do not silently deviate.

---

## Documentation Creation

### Rules
- Every public function, class, and module must have a docstring or JSDoc comment explaining **what** it does and **why**, not just restating the code.
- API endpoints must document: method, route, auth requirement, request body shape, response shape, and possible error codes.
- Complex business logic (especially projection calculations and month-switch logic) must include inline comments explaining the formula and referencing the backend contract section.
- When adding a new feature, update the relevant contract document **first**, then implement. Code without a contract update is incomplete.
- README.md must always reflect the current setup instructions, environment variables, and run commands. Stale documentation is a bug.

### Format
- Use Markdown for all documentation.
- Use tables for structured data (API params, config options).
- Use code blocks with language tags for all code examples.
- Keep sentences short. One idea per sentence. No filler.

---

## Test-Driven Development (TDD)

### Non-Negotiable Rules
- **No production code without a failing test first.** If you write implementation before the test, delete the implementation and start over.
- Tests must be written for: all API endpoints, all business logic functions, all data model validations, and all auth flows.
- Frontend tests are required for: projection calculation displays, form validation logic, and month-switch UI behavior. Visual/layout testing is optional.
- Every bug fix must include a regression test that reproduces the bug before the fix.
- Test coverage target: **90% minimum** for backend, **70% minimum** for frontend logic. Coverage below these thresholds is a blocking issue.

### Test Structure
- Backend tests use `pytest` with `pytest-flask` and `pytest-cov`.
- Frontend tests use `vitest` with `@testing-library/preact`.
- Test files mirror the source structure: `app/routes/records.py` → `tests/routes/test_records.py`.
- Each test file must include: setup/teardown fixtures, happy-path tests, error-path tests, and edge-case tests.
- Tests must be deterministic. No flaky tests. No reliance on execution order. No network calls in unit tests.

### Test Naming
- Use the pattern: `test_<function_or_endpoint>_<scenario>_<expected_outcome>`
- Examples:
  - `test_create_record_with_valid_data_returns_201`
  - `test_create_record_with_deleted_concept_returns_422`
  - `test_projection_calculation_with_overspent_budget_uses_actual_amount`

### TDD Cycle
1. **Red**: Write a failing test that describes the desired behavior.
2. **Green**: Write the minimum code to make the test pass. No more.
3. **Refactor**: Clean up the code while keeping all tests green.
4. **Contract check**: Verify the behavior matches the contract. If not, fix the code or flag the contract discrepancy.

---

## Security Posture

This is a finance application. Security is not optional. Every agent must treat security as a first-class requirement.

### SQL Injection
- **Never** construct SQL queries with string concatenation or f-strings.
- **Always** use SQLAlchemy's ORM or query parameterization.
- Raw SQL is prohibited unless absolutely necessary, and must use bound parameters.
- Any use of `text()` in SQLAlchemy must be reviewed and justified in a comment.

### Authentication & Session Security
- Session cookies must be set with `HttpOnly=True`, `Secure=True` (in production), and `SameSite=Lax`.
- The `SECRET_KEY` must be loaded from an environment variable. Never hardcode it. Never commit it.
- Password hashing must use `werkzeug.security` (generate_password_hash / check_password_hash) with the default method (pbkdf2). Do not use MD5, SHA1, or unsalted hashes.
- The `must_change_password` condition is not a stored flag. It is derived at login (API_SURFACE.md § Force Password Change), kept in the server-side session, and enforced server-side on every authenticated request, not just client-side.
- Logout must invalidate the session server-side, not just clear the cookie client-side.

### API Abuse Prevention
- All endpoints must validate and sanitize input. Never trust request data.
- Type validation is mandatory: check types, lengths, ranges, and allowed values before processing.
- The `DELETE /api/v1/settings/users/:id` endpoint must prevent deletion of the last admin user and self-deletion. `PATCH` must prevent removing `is_admin` from the last admin. These are hard constraints.
- Bulk delete endpoints (`DELETE /api/v1/records?type=&ids=`, `DELETE /api/v1/settings/concepts?ids=`) must cap the number of IDs accepted per request (max 100). Requests exceeding this return `422 VALIDATION_ERROR`.
- Rate limiting is not currently implemented, but all endpoints must be structured to support it in the future (no side effects in GET requests).

### Input Validation
- String inputs must be stripped of leading/trailing whitespace and validated against max lengths.
- The `currency` field must be validated as exactly one grapheme cluster. Use a library like `grapheme` or `regex` with `\X` matching. Do not use `len()` for this check.
- Amount fields must be validated as decimals with at most 2 decimal places. Reject floats with excessive precision.
- Date fields must be validated as `YYYY-MM-DD` format. Reject malformed dates.
- Enum fields (`flow`, `theme`) must be validated against their allowed values. Reject unknown values.

### XSS Prevention
- The frontend must never use `dangerouslySetInnerHTML` (or Preact equivalent) with user-supplied data.
- All user-supplied strings (concept names, usernames, real names) must be rendered as text, not HTML.
- API responses must not reflect unvalidated user input in error messages.

### Secrets & Environment
- All secrets (`SECRET_KEY`, database URLs, passwords) must come from environment variables.
- A `.env` file may be used for local development but must be in `.gitignore`.
- A `.env.example` file must exist with placeholder values and comments explaining each variable.
- Never log secrets, passwords, or session tokens. Scrub sensitive data from all log output.

### Dependency Security
- Run `pip audit` and `npm audit` before adding any new dependency.
- Do not add dependencies with known critical CVEs.
- Pin all dependency versions in `requirements.txt` and `package.json`. No wildcard versions.

---

## Architecture Constraints

### Contract Compliance
- The three contracts (FRONTEND, API_SURFACE, BACKEND) are the single source of truth for behavior.
- Do not add features, endpoints, fields, or behaviors not described in the contracts.
- Do not remove or modify contract-defined behavior without explicit approval.
- If a contract gap is discovered during implementation, document it and propose a contract amendment. Do not invent a solution silently.

### What NOT to Do
- **Do not** add JWT, bearer tokens, or API keys. Auth is session-based. Period.
- **Do not** hard-delete through the API. Users, concepts, transactions and budgets are all soft-deleted (`is_deleted`). Physical removal is reserved for a future manual prune CLI.
- **Do not** add trash, restore, or undo for soft-deleted records. Soft delete exists for consistency, not recovery.
- **Do not** add pagination beyond what the contract defines: record lists use `page` + `q` (`10`, `20`, `50`, `all`). Concepts and users lists are not paginated.
- **Do not** add WebSocket or SSE. The frontend polls for month changes.
- **Do not** add multi-currency support, currency conversion, or locale-aware number formatting.
- **Do not** add audit trails or versioning.
- **Do not** add email notifications, password recovery emails, or any external communication.
- **Do not** introduce a frontend framework other than Preact. No React, no Vue, no Svelte.
- **Do not** add a state management library (Redux, MobX, Zustand) unless the contract requires it. Use Preact signals, context, or component-local state.
- **Do not** use `any` type in TypeScript. Strict mode is enabled and must remain enabled.

### Separation of Concerns
- Backend routes handle HTTP concerns (parsing, validation, status codes). Business logic lives in service functions. Models handle persistence.
- Frontend components handle rendering. Data fetching uses a dedicated API layer. Business logic (calculations, validations) lives in utility functions, not components.
- No SQL in route handlers. No HTML in Python. No direct DOM manipulation in Preact components (use refs only when unavoidable).

---

## Code Style & Conventions

### Python (Backend)
- Follow PEP 8. Use `black` for formatting, `flake8` for linting, `mypy` for type checking.
- All functions must have type hints. `mypy --strict` must pass.
- Use snake_case for functions and variables. Use PascalCase for classes.
- Keep functions under 30 lines. If longer, refactor into smaller functions.
- Use f-strings for string formatting. No `%` formatting or `.format()`.
- Import order: stdlib → third-party → local. Use `isort` to enforce.

### TypeScript (Frontend)
- Follow the project's `tsconfig.json`. Strict mode is non-negotiable.
- Use `camelCase` for functions and variables. Use `PascalCase` for components and types.
- Use `const` by default. Use `let` only when reassignment is necessary. Never use `var`.
- Prefer functional components with hooks. No class components.
- Extract reusable logic into custom hooks. Keep components focused on rendering.
- Use named exports, not default exports, for all components and utilities.

### File Structure
```
venn-manager/
├── backend/
│   ├── app/
│   │   ├── __init__.py          # Flask app factory
│   │   ├── models/              # SQLAlchemy models
│   │   ├── routes/              # API route handlers
│   │   ├── services/            # Business logic
│   │   ├── middleware/          # Auth, error handling
│   │   └── utils/               # Helpers, validators
│   ├── tests/
│   │   ├── routes/
│   │   ├── services/
│   │   └── models/
│   ├── migrations/              # Alembic migrations
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/          # Preact components
│   │   ├── hooks/               # Custom hooks
│   │   ├── api/                 # API client functions
│   │   ├── utils/               # Helpers, formatters
│   │   ├── types/               # TypeScript type definitions
│   │   └── styles/              # Global CSS, Tailwind config
│   ├── tests/
│   ├── index.html
│   ├── vite.config.ts
│   ├── tsconfig.json
│   └── package.json
├── CONTRACTS/
│   ├── FRONTEND.md
│   ├── API_SURFACE.md
│   └── BACKEND.md
├── docs/
├── AGENTS.md
└── README.md
```
> Under docs, store user documentation for both backend and frontend.

---

## Dependency Policy

### Approved Dependencies
**Backend:**
- `flask`, `flask-sqlalchemy`, `flask-migrate`, `flask-login`, `flask-cors`
- `werkzeug` (comes with Flask)
- `pytest`, `pytest-flask`, `pytest-cov` (testing)
- `black`, `flake8`, `mypy`, `isort` (tooling)
- `grapheme` or `regex` (currency validation)

**Frontend:**
- `preact`, `preact-router` or `wouter-preact`
- `@tanstack/preact-query` (data fetching)
- `tailwindcss`, `@tailwindcss/vite`
- `typescript`, `vite`, `@preactjs/preset-vite`
- `vitest`, `@testing-library/preact` (testing)

### Adding New Dependencies
- Justify the need in a comment or documentation.
- Check for known vulnerabilities (`pip audit` / `npm audit`).
- Prefer stdlib or existing approved dependencies over new ones.
- No dependency may be added solely for convenience if the task can be done in <20 lines of code.

---

## Commit Conventions

- Use [Conventional Commits](https://www.conventionalcommits.org/).
- Format: `<type>(<scope>): <description>`
- Types: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `security`
- Scope: `backend`, `frontend`, `api`, `auth`, `docs`, `ci`
- Examples:
  - `feat(backend): add projection calculation endpoint`
  - `fix(frontend): correct month-switch date clamping`
  - `test(api): add regression test for soft-deleted concept lookup`
  - `docs(contract): amend budget section to clarify date picker`
- Each commit must be atomic. One logical change per commit. No mixed commits.
- Commit messages must be imperative mood: "add feature" not "added feature".
- Never commit secrets, `.env` files, or generated artifacts.

---

## Environment & Secrets

- All configuration comes from environment variables. No hardcoded values.
- Required environment variables:
  - `SECRET_KEY` — Flask session secret. Must be random, at least 32 bytes.
  - `DATABASE_URL` — SQLAlchemy connection string.
  - `FLASK_ENV` — `development` or `production`.
  - `DEFAULT_ADMIN_USERNAME` — first-run seed username.
  - `DEFAULT_ADMIN_PASSWORD` — first-run seed password.
- `.env.example` must document every variable with a description and placeholder.
- In production, `Secure` cookie flag must be enabled. In development, it may be disabled for localhost testing.
- Never log environment variable values. Never include them in error responses.

---

## Performance Guardrails

- Prevent N+1 queries. Use SQLAlchemy's `joinedload` or `selectinload` for relationships accessed in loops.
- Add database indexes on: `Transaction.date`, `Transaction.concept_id`, `Budget.date`, `Budget.concept_id`, `Concept.name`.
- Paginated list endpoints return at most 50 records per page. `q=all` is the explicit user-requested exception defined in API_SURFACE.md. Do not add other unbounded list endpoints.
- Frontend must not re-fetch data on every component render. Use `@tanstack/preact-query` caching with appropriate `staleTime`.
- Avoid loading all records into memory for projection calculations. Use database aggregation (`SUM`, `GROUP BY`) where possible.

---

## Accessibility Baseline

- All interactive elements must be keyboard-accessible. No click-only interactions.
- Use semantic HTML: `<button>` for actions, `<table>` for grids, `<label>` for form fields.
- Color contrast must meet WCAG AA standards (4.5:1 for normal text, 3:1 for large text).
- The light, dark, and system themes must all meet contrast requirements.
- Form inputs must have associated labels. Error messages must be linked to their inputs via `aria-describedby`.
- Modal dialogs must trap focus and be dismissible via Escape key.
- Do not convey information through color alone. Use icons, text, or patterns alongside color indicators.

---

## Error Handling Patterns

### Backend
- Every API response, success or error, uses the envelope defined in API_SURFACE.md:
  ```json
  { "data": null, "error": { "code": "ERROR_CODE", "message": "Human-readable description" }, "meta": null }
  ```
- Error codes and statuses are the ones in API_SURFACE.md (e.g. `422 VALIDATION_ERROR` for invalid input, `410 GONE` for soft-deleted targets).
- Never expose stack traces, SQL queries, or internal paths in error responses.
- Log full error details server-side. Return sanitized messages to the client.
- Use HTTP status codes correctly. Do not return `200 OK` with an error body.
- Wrap all route handlers in a global error handler that catches unhandled exceptions and returns `500 Internal Server Error` with a generic message.

### Frontend
- All API calls must handle loading, success, and error states.
- Error messages must be user-friendly and localized via the l10n system. Never display raw error codes or stack traces to the user.
- Network failures must be retried automatically (via `@tanstack/preact-query` retry config) with a maximum of 3 attempts.
- Form validation errors must be displayed inline next to the relevant field, not as a generic alert.

---

## Agent Behavior Rules

- When uncertain about a requirement, check the contracts first. If the contracts don't cover it, ask. Do not guess.
- When making a change that affects multiple files, list all affected files before proceeding.
- Never delete or overwrite existing code without confirming it's not referenced elsewhere.
- When fixing a bug, reproduce it with a test first. Then fix. Then verify the test passes.
- Do not refactor code outside the scope of the current task. If you see something that needs refactoring, note it and move on.
- Do not optimize prematurely. Write clear, correct code first. Optimize only when a performance issue is identified and measured.
- If a task is ambiguous or underspecified, stop and ask for clarification. Do not proceed on assumptions.