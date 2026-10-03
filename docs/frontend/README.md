# Frontend

Venn Manager's UI. Preact, Vite, TypeScript (strict), Tailwind CSS v4,
TanStack Query.

The behaviour contract is `CONTRACTS/FRONTEND.md`; the wire contract it consumes
is `CONTRACTS/API_SURFACE.md`.

## Setup

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173, proxying /api to :5000
```

The backend must be running on `http://127.0.0.1:5000`. The dev server proxies
`/api` to it, so the browser only ever sees one origin and the session cookie can
stay `SameSite=Lax`. There is deliberately no CORS configuration — see
`../backend/CONTRACT_NOTES.md` § 10.

## Commands

| Command             | Purpose                                        |
|---------------------|------------------------------------------------|
| `npm run dev`       | Dev server with HMR and the API proxy          |
| `npm run build`     | Type-check, then bundle into `dist/`           |
| `npm run preview`   | Serve the production bundle locally            |
| `npm run typecheck` | `tsc --noEmit` under strict mode               |
| `npm test`          | Vitest, single run                             |
| `npm run test:watch`| Vitest, watch mode                             |
| `npm run coverage`  | Vitest with v8 coverage and thresholds         |
| `npm audit`         | Known-CVE scan                                 |

There is no linter: AGENTS.md approves none for the frontend, so `tsc --noEmit`
in strict mode is the static gate. `any` is banned by that same strictness.

## Layout

```
src/
├── api/          one module per contract section, plus the envelope client
├── components/   screens and the shared grid, dialog and field primitives
├── hooks/        TanStack Query wrappers; the only place that owns cache keys
├── l10n/         translation keys and locale files
├── styles/       Tailwind entry point and the theme tokens
├── types/        the API's wire types
└── utils/        framework-free logic: money, months, validation
```

AGENTS.md § Separation of Concerns: components render, `api/` fetches, and
calculations live in `utils/`. No component does arithmetic on money or dates,
and no component builds a URL.

## Design notes

**Server-side state only.** Every setting is persisted through
`PATCH /settings`; nothing lives in `localStorage`. A refresh, a second tab or a
second device all show the stored values, which is what API_SURFACE.md § Settings
Persistence requires.

**Money.** The API sends two-decimal numbers and the UI renders them with
`toFixed(2)` — no `Intl.NumberFormat`, no locale grouping, because AGENTS.md
forbids locale-aware number formatting. A budget with no reserved amount renders
as empty, not as `0.00`; the two mean different things.

**Dates.** Rendered as the API's `YYYY-MM-DD`. The only transform is the budget
display rule: a stored date is shown inside the working month with its day
clamped (`utils/months.clampDateToMonth`), so a budget on the 31st appears on the
28th in February and on the 31st again in March. The stored value is never
rewritten.

**Graphemes.** The currency field is validated with `Intl.Segmenter`, not
`.length`, so a ZWJ emoji counts as the single symbol it is and `"USD"` is
rejected (FRONTEND.md § 5.1.3).

**Theme.** `light`, `dark` and `system` all resolve to a `data-theme` attribute
on `<html>`; Tailwind's `dark` variant is bound to that attribute. Resolving
`system` once in JavaScript keeps the CSS free of media-query duplication, and
all three themes meet WCAG AA contrast.

**Caching.** One QueryClient, a 30-second `staleTime`, and no refetch on window
focus. Retries apply to network failures only, at most three attempts in total —
a 409 or a 422 is a definite answer and repeating it changes nothing.

**Month polling.** `GET /current-month` is polled every 60 seconds. There is no
WebSocket or SSE (AGENTS.md § What NOT to Do).

**Accessibility.** Real `<table>`, `<label>` and `<button>` elements throughout;
errors are linked to their field with `aria-describedby` and announced with
`role="alert"`; the modal traps focus and closes on Escape; deleted concepts and
users are marked with a text tag rather than colour alone.

## Interpretations

Details FRONTEND.md leaves open. Anything that changes contract behaviour is in
`../backend/CONTRACT_NOTES.md` instead.

| Question | Decision |
|----------|----------|
| Node and Vite versions | Vite is pinned to 6.x because Vite 7+ requires Node ^20.19 or ≥22.12 and the project toolchain runs Node 20.17. Bump `vite`, `vitest`, `@vitest/coverage-v8` and `jsdom` together after a Node upgrade. |
| Router | `wouter-preact`: hook-based, smaller and maintained. Both options are approved by AGENTS.md. |
| Coverage thresholds | Applied to `src/utils`, `src/api`, `src/hooks` and `src/l10n` — the "frontend logic" AGENTS.md sets at 70%. Screens are reported but not gated, since visual/layout testing is optional. |
| Editing a record | Inline, in the row, per FRONTEND.md § 1.3.2. Adding uses a modal, because a new row does not exist yet. |
| History's picker | A native `<input type="month">` bounded to `earliest_month`…(working month − 1). On first entry the screen shows the working month, which the picker cannot select. When the range is empty the input is disabled and the legend reads "No previous months to show". |
| Concepts and users grids | Searchable client-side, not paginated. API_SURFACE.md paginates record lists only. |
| Forced-change screen | `GET /auth/session` stays restricted during a forced change, so a refresh sees a 403. `App` branches on the `PASSWORD_CHANGE_REQUIRED` code to show the password form rather than the login screen, and that form offers a Log out button — the exemption API_SURFACE.md grants. |
| Currency symbol | Prefixed, unspaced: `€1250.00`. The symbol is display-only and never used in a calculation. |
| Required-field marker | Conveyed by `required`/`aria-required`, not by an asterisk in the label, so the accessible name stays the field name. |
