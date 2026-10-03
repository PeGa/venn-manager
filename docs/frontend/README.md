# Frontend

The Venn Manager web client. Behavior is defined in `CONTRACTS/FRONTEND.md`; the look comes from the design tokens in `src/styles/index.css`. This page covers setup, layout and how to change things.

## Setup

Node 24 (see `.nvmrc`).

```bash
cd frontend
npm ci
npm run dev          # http://localhost:5173, proxies /api to http://127.0.0.1:8000
```

Start the backend first (`docs/backend/README.md`). The dev server proxies `/api`, so the browser sees one origin and the session cookie stays `SameSite=Lax`.

## Quality gates

```bash
npm test             # vitest
npm run coverage     # fails below 70% on src/domain, src/adapters, src/l10n
npm run typecheck    # tsc --noEmit, strict
npm run lint         # eslint with the Solid rules
npm run build        # type check and production bundle in dist/
```

## Layout

The frontend is hexagonal (AGENTS.md § Hexagonal architecture).

| Path | Holds |
|---|---|
| `src/domain/` | Pure logic: money, amount parsing, dates, budget figures and notes, selection, activity sentences, pie geometry, the data model |
| `src/ports/api.ts` | The `Api` interface every screen uses, and `ApiError` |
| `src/adapters/http.ts` | `Api` over `fetch` |
| `src/adapters/queries.ts` | Query keys, retry policy, the query client |
| `src/l10n/` | Translation keys. `en.ts` defines the key set; `es.ts` is typed against it |
| `src/ui/` | The app root, shell, screens and shared components |
| `src/styles/index.css` | Design tokens as CSS variables, light and dark |
| `tests/` | Mirrors `src/`. `tests/ui/fakeApi.ts` is an in-memory `Api` for screen tests |

## Common changes

**A new string.** Add the key to `src/l10n/en.ts` and `src/l10n/es.ts`. TypeScript fails until both have it.

**A new field from the API.** Add it to the type in `src/domain/model.ts`, then show it where needed.

**A new rule or calculation.** Write it in `src/domain/` with tests. Components only render its result.

**A new endpoint.** Add the method to `src/ports/api.ts`, implement it in `src/adapters/http.ts`, and add it to `tests/ui/fakeApi.ts`.

## Design notes

- **One codebase, two layouts.** Width (`max-width: 767px`) switches sidebar and title bar. Pointer type (`pointer: coarse`) switches mouse selection and touch sheets. They are independent.
- **Server state** goes through `@tanstack/solid-query`. Screens refetch when opened and on window focus; there is no polling.
- **Writes** call the API, then invalidate every query. Budget amounts and typed settings save 400 ms after the last change.
- **Lists** are keyed by record id, so a refetch updates rows instead of remounting them mid-edit.
- **Dialogs** use the native `<dialog>`: focus trapping and Escape come from the browser.
- **The dark palette** is derived from the light tokens and is pending review.
