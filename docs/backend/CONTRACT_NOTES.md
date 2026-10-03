# Contract notes

AGENTS.md requires that a gap discovered during implementation be documented
and a contract amendment proposed, rather than resolved silently. This file is
that record. Nothing here changes contract-defined behaviour; every entry is
either an unspecified detail or a discrepancy between a rule and the library it
names.

Entries are ordered by how much they matter. Items 1, 3 and 4 were put to the
project owner and **decided on 2026-09-26**; the contracts were amended to match
and the code follows the amended text. They are kept here as the record of why
the contracts say what they now say.

**Item 11 is the one entry that was a defect rather than an unspecified detail.**
If you only read one, read that.

---

## 1. Password hash method — RESOLVED: scrypt

**The problem:** AGENTS.md said "with the default method (pbkdf2)", but Werkzeug
3.x changed its implicit default to scrypt, so the two halves of the sentence
contradicted each other.

**Decision (2026-09-26):** use scrypt, and fix the rule rather than pin a weaker
method to match an outdated default.

**Now:** AGENTS.md reads "the library's default method (scrypt since Werkzeug
3.x) … Do not pin a weaker method to match an older default."
`CONTRACTS/BACKEND.md` § 4.1 says the same. `app/models/user.py` sets
`HASH_METHOD = "scrypt"`, which werkzeug expands to n=32768, r=8, p=1 — about
87 ms and 34 MB per hash. Tests assert the `scrypt:` prefix, so a silent change
of method fails the suite.

`tests/conftest.py` lowers the work factor to `scrypt:1024:8:1` for the suite
only. Same algorithm, salt handling and storage format; the parameters travel
inside each hash, so verification still exercises the real path.

---

## 2. Server-side session invalidation

**AGENTS.md says:** "Logout must invalidate the session server-side, not just
clear the cookie client-side." **API_SURFACE.md says:** a soft-deleted user's
"sessions are invalidated".

**Gap:** Flask's session is a signed cookie held by the browser. There is no
server-side session store, so clearing the cookie cannot invalidate a copy an
attacker already took. The reference schema has no field for it either.

**Implemented:** a per-user counter in the existing generic `settings` table,
under the internal key `session_epoch` (`app/services/sessions.py`). A cookie
carries the epoch it was issued with; the user loader rejects a mismatch. It is
bumped on logout, on a self-service password change, on an admin-initiated
password reset, and on user deletion.

No column was added and no endpoint exposes it: `GET /settings` never returns
the key and `PATCH /settings` rejects it as unknown.

**Behaviour worth knowing:** bumping the epoch invalidates *every* session of
that user, not just the current one. For a trusted-household app this is the
desirable reading, and it is what makes "their sessions are invalidated" true.

**Proposed amendment:** document `session_epoch` as an internal settings key in
API_SURFACE.md § 3.1 so the mechanism is part of the contract.

---

## 3. The force-password-change gate blocked logout — RESOLVED: logout exempt

**API_SURFACE.md says:** "all endpoints except `POST /api/v1/auth/password`
return `PASSWORD_CHANGE_REQUIRED`".

**Decision (2026-09-26):** exempt logout. Leave `GET /auth/session` restricted.

**Now:** API_SURFACE.md § Force Password Change, the `POST /auth/logout` section
and the endpoint summary all list the two permitted endpoints.
`GATE_EXEMPT_ENDPOINTS` in `app/middleware/auth.py` matches, and
`tests/middleware/test_auth.py` pins both halves — logout succeeds, session still
returns 403.

**Consequence for the frontend:** because `/auth/session` stays restricted, a
refresh on the forced-change screen sees a 403, not a payload. `App` therefore
branches on the `PASSWORD_CHANGE_REQUIRED` code
(`api/client.isPasswordChangeRequired`) to show the password form instead of the
login screen, and that screen offers a Log out button so the exemption is
reachable. Both behaviours are covered by `tests/components/App.test.tsx`.

---

## 4. Password length policy — RESOLVED: 8–128

**The problem:** the contracts rejected a password that was "too short" without
ever giving a number.

**Decision (2026-09-26):** keep the 8-character floor.

**Now:** API_SURFACE.md states the bounds at `POST /auth/password` — "8 to 128
characters and must differ from `current_password`. The same bounds apply to
every other password field in this API" — and § 3.2 repeats them for user
creation. `app/utils/validation.py` holds the constants, and the frontend mirrors
them in `utils/validation.ts` so a submission is rejected in the browser before
the server has to.

---

## 5. Status codes outside the documented set

**API_SURFACE.md says:** "HTTP status codes are still used for transport
semantics (200, 201, 401, 403, 404, 409, 410, 422, 500)" and defines eight error
codes. Werkzeug can still produce 400, 405 and 415, none of which are listed.

**Implemented** (`app/middleware/errors.py`), folding them into the documented
set:

| Werkzeug | Reported as                     | Rationale                              |
|----------|---------------------------------|----------------------------------------|
| 400      | 422 `VALIDATION_ERROR`          | A malformed body is a validation failure |
| 415      | 422 `VALIDATION_ERROR`          | Same, at the content-type level        |
| 405      | 404 `NOT_FOUND`                 | The resource+method pair does not exist |

The envelope shape is identical either way, so the frontend is unaffected.

**Proposed amendment:** add the mapping table to API_SURFACE.md § Error Codes.

---

## 6. Search case sensitivity

**API_SURFACE.md says:** `search` is a "substring match against concept name".
**FRONTEND.md says:** grids filter by "a specific substring". Neither mentions
case.

**Implemented:** case-insensitive, via `lower()` on both sides. This also makes
behaviour identical on SQLite (ASCII-case-insensitive `LIKE`) and PostgreSQL
(case-sensitive `LIKE`), which a literal reading would not. Submitted `%` and
`_` are escaped, so they cannot widen the match.

**Proposed amendment:** state "case-insensitive substring match".

---

## 7. Payload field sets differ between the examples

**API_SURFACE.md** shows `created_by_is_deleted` in the `GET /settings/concepts`
example but not in the `POST`/`PATCH` examples, and shows
`concept_is_deleted`/`user_is_deleted` in the canonical "Record shape" section
but not in the `GET /records` example.

**Implemented:** one representation per resource, matching the fullest example —
the `GET` list shape for concepts, the canonical record shape for records. A
newly created concept's creator is by definition not deleted, so the extra field
is `false` and harmless.

**Proposed amendment:** note that the examples are abbreviated and the canonical
shape applies to every payload for that resource.

---

## 8. Bulk delete and deleted concepts

**BACKEND.md § 1.2 says:** "Records of a deleted concept cannot be edited or
deleted. The backend returns 410." **§ 5.4** describes bulk delete but only
mentions "any missing id → 404, any already-deleted id → 410".

**Implemented:** bulk delete applies the same 410 rule as single delete when any
target's concept is soft-deleted. All-or-nothing, so nothing is written. Such
records are invisible in the working month anyway; this only closes the hole for
history.

---

## 9. Smaller unspecified details

| Detail | Decision |
|--------|----------|
| Duplicate ids in a bulk delete | Collapsed. The 100-id cap applies to distinct ids. |
| `must_change_password` user count | Non-deleted users. Identical in practice: the gate blocks user creation, so a second user can only exist after the password changed. |
| Field length limits | `username` 64 (matches `concept.name`), `real_name` 128, `password` 128. |
| Empty `PATCH` body | 422 on settings, users and records. A no-op write is a client bug. |
| Unknown field in a `PATCH` body | 422. Includes `username` on `/settings/users/:id` (profile keys belong to `PATCH /settings`) and `flow` on a record. |
| `q=all` together with `page` | `page` is normalised to 1 in `meta`; paging a complete list is meaningless. |
| Negative amounts | Accepted. The contracts never forbid them and flow comes from the concept. Range is still `DECIMAL(10,2)`. |
| Amount type on the wire in | JSON numbers and numeric strings are both accepted on input, because a browser number input yields a string. Booleans are rejected explicitly — Python would read `true` as `1`. |
| `earliest_month` | Oldest non-deleted transaction, regardless of its concept's state. Literal reading of API_SURFACE.md § 2. |
| Concept name uniqueness | Exact match after trimming, per `(name, flow)`, case-sensitive. The contract says "same name and flow". |
| Currency symbol | Stripped, then required to be exactly one grapheme cluster. A multi-codepoint emoji is accepted; `"USD"` is not. |

---

## 10. Dependencies deliberately not added

| Dependency | Why not |
|------------|---------|
| `flask-cors` | The Vite dev server proxies `/api` to the backend, so the browser sees one origin. A real cross-origin deployment would force `SameSite=None`, breaking the `SameSite=Lax` requirement in AGENTS.md. |
| `python-dotenv` | `app/utils/env.py` loads `.env` in about 15 lines, under the 20-line threshold AGENTS.md sets for refusing a convenience dependency. |

`pip-audit` reports no known vulnerabilities for the runtime set.

---

## 11. Projections treated "no actual" as an actual of zero — RESOLVED

**Found by:** the project owner using the app on 2026-09-27, not by a test. Two
budgets (IN 100, OUT 10) and no transactions produced `earn_projection = 0` and
`savings_projection = -10`.

**Why the contract produced it:** § 2.2 said to add `min(budget, actual)` for IN
concepts and `max(budget, actual)` for OUT. Both were written assuming `actual`
meant an *existing* outcome. With no transactions the implementation coerced the
missing actual to `0`, so:

- OUT: `max(10, 0) = 10` — the right number, by accident.
- IN: `min(100, 0) = 0` — asserting an income shortfall that had not happened.

The asymmetry hid the defect: the spend widget looked correct, so the coercion
was never questioned, while the earnings widget reported zero income on the first
day of every month and made `savings_projection` negative by the entire spend
budget before any income could have arrived.

**Decision (2026-09-27):** a missing actual is not an actual of zero. When a
budgeted concept has no transactions in the target month, project the budget — in
both flows. Once any transaction exists, compare normally with `max` (OUT) or
`min` (IN). A recorded `0` transaction *is* an actual and still projects `0`, as
does a concept whose only transactions are soft-deleted.

**Changed:** `CONTRACTS/API_SURFACE.md` § 5 algorithm and rationale,
`CONTRACTS/BACKEND.md` § 2.2, and `app/services/projections.py`. The fallback is
now explicit in both branches rather than incidental to `max`.

**Regression tests:** `TestMissingActual` in `tests/routes/test_projections.py`
reproduces the reported figures end to end, and
`test_out_fallback_is_explicit_not_a_max_coincidence` uses a negative budget — the
one input where `max(budget, 0)` and "project the budget" disagree — so a future
refactor back to the bare `max` cannot pass.

**Lesson worth keeping:** the contract's own rationale described `min` and `max`
as "pessimistic", which reads as intentional and discouraged scrutiny. The defect
was not in the pessimism, it was in the domain of the operands. A formula stated
over "the actual amount" must say what happens when there is no actual.
