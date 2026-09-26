# Venn Manager — Backend API Contract v1

## General

- **Base URL:** `/api/v1`
- **Transport:** REST over HTTP. Flask + SQLAlchemy backend. Preact frontend consumes this API.
- **Design principle:** Hexagonal. This contract defines the **ports** (endpoints, request/response shapes). Domain logic (projections, month detection, concept validation) lives in a core layer independent of Flask, JSON, or HTTP. Adapters (Flask routes, SQLAlchemy repositories) implement these ports. A change to color theme logic must never require modifying an API route definition.
- **Auth mechanism:** Session-based via cookies. No JWT.
- **Currency note:** All monetary values are `DECIMAL(10,2)`. The currency symbol is a display-only setting and is never used in calculations. Assume `0.1 + 0.2 = 0.3`.

---

## Response Envelope

Every response, regardless of HTTP status code, follows this exact shape:

```json
{
  "data": <object | array | null>,
  "error": <{ "code": "STRING_CODE", "message": "Human readable description" } | null>,
  "meta": <object | null>
}
```

- On success: `error` is `null`. `data` contains the payload.
- On error: `data` is `null`. `error` contains the code and message.
- `meta` is used for pagination info. `null` when not applicable.

HTTP status codes are still used for transport semantics (200, 201, 401, 403, 404, 409, 410, 422, 500), but the frontend always parses the same JSON structure.

### Error Codes

| code                | HTTP | Meaning                          |
|---------------------|------|----------------------------------|
| UNAUTHORIZED        | 401  | Not authenticated                |
| FORBIDDEN           | 403  | Authenticated but not permitted  |
| PASSWORD_CHANGE_REQUIRED | 403 | Must change password before proceeding |
| NOT_FOUND           | 404  | Resource does not exist          |
| CONFLICT            | 409  | Duplicate or state conflict      |
| GONE                | 410  | Target was soft-deleted. Message: "Record not available anymore." |
| VALIDATION_ERROR    | 422  | Request body failed validation   |
| INTERNAL_ERROR      | 500  | Unexpected server error          |

### Pagination

Query parameters on list endpoints:

- `page` — integer, 1-indexed. Default: `1`.
- `q` — integer (`10`, `20`, `50`) or the literal string `all`. Default: `10`.

When `q` is numeric, `meta` contains:

```json
{
  "meta": {
    "page": 1,
    "per_page": 10,
    "total": 42,
    "total_pages": 5
  }
}
```

When `q=all`, `per_page` equals the total count and `total_pages` is `1`.

### Date/Time Format

- Dates: `YYYY-MM-DD`
- Timestamps: ISO 8601 UTC, e.g. `2025-07-15T10:30:00Z`
- Month identifiers: `YYYY-MM`, e.g. `2025-07`

---

## 1. auth

Handles login, logout, session validation, and password changes.

### POST /api/v1/auth/login

Authenticates a user and establishes a session cookie.

**Request body:**
```json
{
  "username": "string",
  "password": "string"
}
```

**Success (200):**
```json
{
  "data": {
    "user": {
      "id": 1,
      "username": "admin",
      "real_name": "Administrator",
      "is_admin": true
    },
    "must_change_password": true
  },
  "error": null,
  "meta": null
}
```

Sets the session cookie. `must_change_password` is derived at login (see Business Logic § Force Password Change). It is not a stored database flag.

**Error (401):**
```json
{
  "data": null,
  "error": { "code": "UNAUTHORIZED", "message": "Invalid username or password" },
  "meta": null
}
```

A soft-deleted user cannot log in. The response is the same 401 as for invalid credentials.

### POST /api/v1/auth/logout

Clears the session cookie and invalidates the session server-side.

**Success (200):**
```json
{
  "data": null,
  "error": null,
  "meta": null
}
```

### GET /api/v1/auth/session

Returns the current session state. Used by the frontend on load to determine authentication.

**Success (200):**
Same shape as login success response.

**Error (401):**
```json
{
  "data": null,
  "error": { "code": "UNAUTHORIZED", "message": "No active session" },
  "meta": null
}
```

### POST /api/v1/auth/password

Changes the current user's password. This is the **only endpoint permitted** when `must_change_password` is true. All other endpoints return `PASSWORD_CHANGE_REQUIRED` until the password is changed.

**Request body:**
```json
{
  "current_password": "string",
  "new_password": "string"
}
```

**Success (200):**
```json
{
  "data": null,
  "error": null,
  "meta": null
}
```

**Error (401):** `current_password` is incorrect.
**Error (422):** `new_password` does not meet requirements (e.g. too short, same as current).

---

## 2. current_month

Tracks the application's current month and whether a month switch is pending.

### GET /api/v1/current-month

Returns the server's current month and whether the user needs to acknowledge a month change.

**Success (200):**
```json
{
  "data": {
    "current_month": "2025-07",
    "last_acknowledged_month": "2025-06",
    "needs_switch": true,
    "earliest_month": "2025-03"
  },
  "error": null,
  "meta": null
}
```

- `current_month`: derived from server date.
- `last_acknowledged_month`: the last month the user confirmed. Stored in settings (see § settings). This is the user's **working month**: Home and Budget operate on it, and History treats every earlier month as a previous month.
- `needs_switch`: `true` when `current_month != last_acknowledged_month`.
- `earliest_month`: the month of the oldest non-deleted transaction, or `null` if there are none. History offers months from `earliest_month` up to the month before `last_acknowledged_month`. If that range is empty, History shows "No previous months to show".

### POST /api/v1/current-month/switch

Acknowledges the month change. Updates `last_acknowledged_month` to match `current_month`. **No data modification occurs.** No transactions are archived. No budget dates are altered. This is purely a state signal.

**Success (200):**
```json
{
  "data": {
    "current_month": "2025-07",
    "last_acknowledged_month": "2025-07",
    "needs_switch": false,
    "earliest_month": "2025-03"
  },
  "error": null,
  "meta": null
}
```

**Error (409):** `current_month` already equals `last_acknowledged_month`. Nothing to switch.

---

## 3. settings

All configuration: global settings, per-user profile settings, user management, and concept management.

### 3.1 General Settings

#### GET /api/v1/settings

Returns all settings relevant to the current user: global settings merged with user-specific settings.

**Success (200):**
```json
{
  "data": {
    "currency": "$",
    "language": "en",
    "theme": "dark",
    "last_acknowledged_month": "2025-07",
    "username": "admin",
    "real_name": "Administrator"
  },
  "error": null,
  "meta": null
}
```

#### PATCH /api/v1/settings

Updates one or more settings. The backend determines scope (global vs per-user) based on the key.

**Request body:**
```json
{
  "currency": "€",
  "language": "es"
}
```

**Success (200):**
```json
{
  "data": {
    "currency": "€",
    "language": "es"
  },
  "error": null,
  "meta": null
}
```

**Error (403):** The setting requires admin and the current user is not admin.
**Error (409):** `username` is already taken (including by a soft-deleted user).
**Error (422):** Invalid value (e.g. currency string exceeds one grapheme cluster), unknown key, or a read-only key.

**Persistence requirement:** All settings changes must be written to the database. A page refresh must reflect the updated values. No setting may exist only in frontend state.

**Setting scopes:**

| key                      | scope    | requires_admin | writable via PATCH |
|--------------------------|----------|----------------|--------------------|
| currency                 | global   | false          | yes                |
| language                 | per-user | false          | yes                |
| theme                    | per-user | false          | yes                |
| username                 | profile  | false          | yes                |
| real_name                | profile  | false          | yes                |
| last_acknowledged_month  | per-user | false          | no (only via `POST /current-month/switch`) |

- `profile` keys are the current user's own `username` and `real_name`. They are stored on the `users` table, not in `settings`. This is how the Profile screen changes them, without a separate endpoint ("profile belongs to settings"). `GET /settings` also returns them.
- `language`: one of the shipped locales (`en`, `es`).
- `theme`: one of `light`, `dark`, `system`.
- User management is not a setting. It is gated by `is_admin` on `/settings/users` (§ 3.2).

Currency changes affect all users. The frontend shows a confirmation dialog before calling this endpoint, but the backend does not enforce that confirmation.

### 3.2 User Management

All endpoints under this path require the admin role. Non-admin users receive `FORBIDDEN`.

#### GET /api/v1/settings/users

Lists all non-deleted users.

**Success (200):**
```json
{
  "data": [
    {
      "id": 1,
      "username": "admin",
      "real_name": "Administrator",
      "is_admin": true
    },
    {
      "id": 2,
      "username": "alice",
      "real_name": "Alice",
      "is_admin": false
    }
  ],
  "error": null,
  "meta": null
}
```

Password hashes are never returned.

#### POST /api/v1/settings/users

Creates a new user.

**Request body:**
```json
{
  "username": "string",
  "real_name": "string",
  "password": "string",
  "is_admin": false
}
```

**Success (201):**
```json
{
  "data": {
    "id": 3,
    "username": "bob",
    "real_name": "Bob",
    "is_admin": false
  },
  "error": null,
  "meta": null
}
```

**Error (409):** Username already exists.
**Error (422):** Validation failure (missing fields, password too short).

#### PATCH /api/v1/settings/users/:id

Updates a user. Admin can change real_name, password, and is_admin for any user.

**Request body (all fields optional):**
```json
{
  "real_name": "string",
  "password": "string",
  "is_admin": true
}
```

**Success (200):**
```json
{
  "data": {
    "id": 2,
    "username": "alice",
    "real_name": "Alice Updated",
    "is_admin": false
  },
  "error": null,
  "meta": null
}
```

**Error (403):** Removing `is_admin` from the last remaining admin.
**Error (404):** User not found.
**Error (410):** User is soft-deleted. Message: "Record not available anymore."
**Error (422):** Validation failure.

#### DELETE /api/v1/settings/users/:id

**Soft-deletes** a user. Sets `is_deleted = true` and invalidates all of that user's sessions. The row stays, so records keep a valid `user_id`. Their username resolves normally and is rendered with a faint "(deleted)" tag. A soft-deleted user cannot log in. Their username stays reserved and cannot be reused.

**Success (200):**
```json
{
  "data": null,
  "error": null,
  "meta": null
}
```

**Error (404):** User not found.
**Error (403):** Attempting to delete the last admin, or attempting to delete oneself.
**Error (410):** User already soft-deleted.

### 3.3 Concept Management

Concepts are the predefined categories that records reference. Users cannot free-type a concept on a record; they must select from existing concepts.

#### GET /api/v1/settings/concepts

Lists concepts. Excludes soft-deleted by default.

**Query parameters:**
- `flow` — optional filter: `in` or `out`
- `include_deleted` — optional boolean, default `false`

**Success (200):**
```json
{
  "data": [
    {
      "id": 1,
      "name": "Groceries",
      "flow": "out",
      "created_by": "admin",
      "created_by_is_deleted": false,
      "created_at": "2025-07-01T08:00:00Z",
      "is_deleted": false
    },
    {
      "id": 2,
      "name": "Salary",
      "flow": "in",
      "created_by": "admin",
      "created_by_is_deleted": false,
      "created_at": "2025-07-01T08:00:00Z",
      "is_deleted": false
    }
  ],
  "error": null,
  "meta": null
}
```

Concepts are a small reference list. This endpoint is not paginated and returns the full list (`meta: null`). The Concepts grid filters it client-side. Pickers use the default (non-deleted) list. The Concepts screen uses `include_deleted=true` when the user asks to see deleted concepts. Those are rendered with a faint "(deleted)" tag.

#### POST /api/v1/settings/concepts

Creates a concept.

**Request body:**
```json
{
  "name": "string (max 64 chars)",
  "flow": "in | out"
}
```

**Success (201):**
```json
{
  "data": {
    "id": 3,
    "name": "Rent",
    "flow": "out",
    "created_by": "admin",
    "created_at": "2025-07-15T10:00:00Z",
    "is_deleted": false
  },
  "error": null,
  "meta": null
}
```

**Error (409):** A non-deleted concept with the same name and flow already exists. A soft-deleted concept's name can be reused.
**Error (422):** Name exceeds 64 chars, invalid flow value, or empty name.

#### PATCH /api/v1/settings/concepts/:id

Updates a concept. **Only the `name` field can be changed.** The `flow` field is immutable after creation. To change a concept's flow, delete it and create a new one.

**Request body:**
```json
{
  "name": "string (max 64 chars)"
}
```

**Success (200):**
```json
{
  "data": {
    "id": 3,
    "name": "Monthly Rent",
    "flow": "out",
    "created_by": "admin",
    "created_at": "2025-07-15T10:00:00Z",
    "is_deleted": false
  },
  "error": null,
  "meta": null
}
```

**Error (404):** Concept not found.
**Error (409):** Another non-deleted concept already has this name and flow.
**Error (410):** Concept is soft-deleted. Message: "Record not available anymore."
**Error (422):** Attempting to modify `flow`, or name exceeds 64 chars.

**Renaming impact:** Renaming a concept affects all records that reference it, since records store `concept_id` and the name is resolved via the foreign key. The frontend must show a confirmation dialog before renaming.

#### DELETE /api/v1/settings/concepts/:id

**Soft-deletes** a concept. Sets `is_deleted = true`. The concept remains in the database to preserve referential integrity with historical records. Soft-deleted concepts do not appear in the concept picker for new records.

Referencing transactions and budgets are **not** mutated. Visibility is derived from the concept's state (see Business Logic § Concept Soft-Delete). The frontend warns before calling this that the concept's budget entries and current-month records will disappear.

**Success (200):**
```json
{
  "data": null,
  "error": null,
  "meta": null
}
```

**Error (404):** Concept not found.
**Error (410):** Concept already soft-deleted.

#### DELETE /api/v1/settings/concepts

**Bulk soft-delete** for the multi-select delete on the Concepts screen. It uses a parameter on the collection path, so no new resource is added.

**Query parameters:**
- `ids` — required. Comma-separated concept ids, 1 to 100 ids.

All-or-nothing: if any id fails, nothing is deleted.

**Success (200):** `data: { "deleted": <count> }`
**Error (404):** At least one id does not exist.
**Error (410):** At least one id is already soft-deleted.
**Error (422):** `ids` missing, malformed, empty, or more than 100.

---

## 4. records

Unified endpoint for both transactions and budgets. The `type` parameter and field distinguish between them. Internally they are separate tables with separate lifecycles; the API presents them through a single port.

### Record shape (response)

```json
{
  "id": 1,
  "type": "transaction | budget",
  "date": "2025-07-15",
  "concept_id": 3,
  "concept_name": "Groceries",
  "concept_flow": "out",
  "concept_is_deleted": false,
  "amount": 45.50,
  "user_id": 1,
  "username": "admin",
  "user_is_deleted": false,
  "created_at": "2025-07-15T10:30:00Z"
}
```

- For `type: "budget"`, `amount` may be `null` (a budget entry without a reserved amount).
- For `type: "transaction"`, `amount` is always a number.
- `concept_name` and `concept_flow` are resolved from the concepts table via `concept_id`.
- `concept_is_deleted` and `user_is_deleted` let the frontend render the faint "(deleted)" tag (Business Logic § Concept Soft-Delete, § User Soft-Delete).
- Soft-deleted records themselves are never returned by any endpoint.

### GET /api/v1/records

Lists records filtered by type, month, and optional search.

**Query parameters:**

| param    | required | description                                    |
|----------|----------|------------------------------------------------|
| type     | yes      | `transaction` or `budget`                      |
| month    | transaction only | `YYYY-MM` — filters transactions by `date`. Required for `type=transaction`. Ignored for `type=budget`. |
| page     | no       | integer, default `1`                           |
| q        | no       | `10`, `20`, `50`, or `all`. Default `10`       |
| search   | no       | substring match against concept name           |

**Success (200):**
```json
{
  "data": [
    {
      "id": 1,
      "type": "transaction",
      "date": "2025-07-15",
      "concept_id": 3,
      "concept_name": "Groceries",
      "concept_flow": "out",
      "amount": 45.50,
      "user_id": 1,
      "username": "admin",
      "created_at": "2025-07-15T10:30:00Z"
    }
  ],
  "error": null,
  "meta": {
    "page": 1,
    "per_page": 10,
    "total": 1,
    "total_pages": 1
  }
}
```

**Filtering behavior:** Search and month filters are applied server-side. A filter on a given month will not return results from a different month. Results are sorted by `id` ascending (creation order). Sort order cannot be changed.

**Budgets are a standing list.** `type=budget` returns every non-deleted budget whose concept is not deleted, regardless of the budget's `date`. The budget `date` is informational. It is never rewritten by the month switch. The frontend displays it in the working month (Business Logic § Month Switch).

**Transactions: working month vs previous months.** The backend compares `month` with the requesting user's `last_acknowledged_month` (the working month):
- `month` ≥ working month: records whose concept is soft-deleted are excluded.
- `month` < working month (History): records whose concept is soft-deleted are included, with `concept_is_deleted: true`.

### POST /api/v1/records

Creates a record.

**Request body:**
```json
{
  "type": "transaction | budget",
  "date": "2025-07-15",
  "concept_id": 3,
  "amount": 45.50
}
```

- `type` is required. Routes to the correct table.
- `amount` is required for `transaction`. Optional (nullable) for `budget`.
- `concept_id` must reference an existing, non-deleted concept. The concept's `flow` is inherited automatically. The frontend does not send `flow`.
- `user_id` is derived from the session. Not sent by the frontend.

**Success (201):**
Returns the created record in standard record shape.

**Error (422):**
- `concept_id` references a deleted or nonexistent concept.
- `amount` is missing for a transaction.
- `date` is invalid.
- Concept's flow is incompatible (should not happen if frontend filters correctly, but backend validates).

### PATCH /api/v1/records/:id

Updates a record.

**Query parameters:**
- `type` — required. `transaction` or `budget`. Routes to the correct table.

**Request body (all fields optional):**
```json
{
  "date": "2025-07-16",
  "concept_id": 4,
  "amount": 52.00
}
```

**Success (200):**
Returns the updated record in standard record shape.

**Error (404):** Record not found for the given id and type.
**Error (410):** Record is soft-deleted, or its concept is soft-deleted. Message: "Record not available anymore."
**Error (422):** Validation failure (same rules as POST).

### DELETE /api/v1/records/:id

**Soft-deletes** a record (`is_deleted = true`). No undo and no restore UI. Soft delete exists for database consistency, not recovery. Physical removal is reserved for a future manual prune CLI.

**Query parameters:**
- `type` — required. `transaction` or `budget`.

**Success (200):**
```json
{
  "data": null,
  "error": null,
  "meta": null
}
```

**Error (404):** Record not found.
**Error (410):** Record already soft-deleted.

### DELETE /api/v1/records

**Bulk soft-delete** for the multi-select delete on Home and Budget. It uses a parameter on the collection path, so no new resource is added.

**Query parameters:**
- `type` — required. `transaction` or `budget`.
- `ids` — required. Comma-separated record ids, 1 to 100 ids.

All-or-nothing: if any id fails, nothing is deleted.

**Success (200):** `data: { "deleted": <count> }`
**Error (404):** At least one id does not exist for the given type.
**Error (410):** At least one id is already soft-deleted.
**Error (422):** `type` or `ids` missing, malformed, empty, or more than 100.

---

## 5. projections

Read-only computed values for a given month. Computed on-the-fly per request. No stored projection values.

### GET /api/v1/projections

**Query parameters:**
- `month` — required. `YYYY-MM`.

**Success (200):**
```json
{
  "data": {
    "spend_projection": 1250.00,
    "earn_projection": 3000.00,
    "savings_projection": 1750.00,
    "actual_spend": 830.50,
    "actual_earn": 3000.00
  },
  "error": null,
  "meta": null
}
```

- `spend_projection`: projected total spending for the month.
- `earn_projection`: projected total earning for the month.
- `savings_projection`: `earn_projection - spend_projection`.
- `actual_spend`: sum of transaction amounts with `flow = out` in the given month.
- `actual_earn`: sum of transaction amounts with `flow = in` in the given month.

Computation logic is defined in Business Logic § Projection Calculation.

---

## Business Logic

### Force Password Change

No stored flag. Derived at login.

**Condition:** The provided password hash matches the default seed password hash **AND** the users table contains exactly one user.

When true:
- Login response includes `must_change_password: true`.
- Session is established but restricted: all endpoints except `POST /api/v1/auth/password` return `PASSWORD_CHANGE_REQUIRED` (403).
- Once the password is changed, the hash no longer matches the default, and the restriction lifts.

If the user later changes their password back to the default, the condition re-triggers only if they are still the sole user. In practice, by that point other users will have been created, so the condition will not fire.

### Projection Calculation

Computed on-the-fly. No cached or stored projection values.

**Inputs:**
- All non-deleted budget entries whose concept is not deleted. Budgets persist across months and are not filtered by month.
- All non-deleted transactions in the target month. Transactions whose concept is soft-deleted are excluded when the target month is the working month (or later). They are **included** when it is a previous month, because previous months stay intact (BACKEND.md § 1.2). Their concept's budgets are excluded, so they count as unbudgeted activity.
- A budget entry with `amount = null` counts as `0`.

**Algorithm:**

```
spend_projection = 0
earn_projection = 0

budget_concept_ids = set of concept_ids that have budget entries

For each concept C that has at least one budget entry:
    budget_amount = sum of budget entry amounts for C (treat null as 0)
    actual_amount = sum of transaction amounts in target month where concept_id = C.id

    if C.flow == "out":
        spend_projection += max(budget_amount, actual_amount)
    elif C.flow == "in":
        earn_projection += min(budget_amount, actual_amount)

For each transaction T in target month where T.concept_id NOT IN budget_concept_ids:
    if T.concept_flow == "out":
        spend_projection += T.amount
    elif T.concept_flow == "in":
        earn_projection += T.amount

savings_projection = earn_projection - spend_projection
```

**Rationale:**
- Spending uses `max(budget, actual)`: pessimistic. If you overspent, the projection reflects the overspend. If you underspent, it assumes you'll still hit the budget.
- Earning uses `min(budget, actual)`: pessimistic. If you earned less than planned, projection reflects the lower actual. If you earned more, it caps at the budget to avoid optimistic inflation.
- Transactions for concepts not in the budget are added directly. They represent unbudgeted activity.

### Month Switch

The month switch is a state signal, not a data operation.

- No transactions are archived, moved, or modified.
- No budget dates are altered. Budget dates are informational. The frontend displays each budget date inside the working month, keeping the stored day and clamping to the month's last day (31 → 30, 29 → 28). The stored day is never lost, so there is no drift (Jan 31 → Feb 28 → Mar 31).
- No budget amounts are reset. Budget entries persist across months.
- The only change: `last_acknowledged_month` in settings is updated to match the current month.
- The "reset" perceived by the user is natural: the new month has no transactions yet, so `actual_spend` and `actual_earn` start at zero. Budget amounts remain, so projections immediately reflect the budget baseline.
- History is simply a query for transactions in a past month. No separate storage or archiving.

### Soft-Delete (All Entities)

- Users, concepts, transactions and budgets are soft-deleted (`is_deleted = true`). Nothing is hard-deleted through the API. A manual prune CLI is deferred.
- A soft-deleted record is never returned by any endpoint and never counts in projections.
- Any `PATCH` or `DELETE` on a soft-deleted target returns `410 GONE` with "Record not available anymore." This is the edit-vs-delete race outcome. Otherwise, last write wins.

### Concept Soft-Delete

- Concepts are soft-deleted (`is_deleted = true`), never hard-deleted.
- This preserves referential integrity for historical transactions and budgets.
- Soft-deleted concepts are excluded from the concept picker when creating new records.
- Soft-deleted concepts still resolve their name and flow when displaying historical records.
- To change a concept's flow, the user must delete it (soft) and create a new concept with the desired flow.
- No data cascade. Referencing records keep `is_deleted = false`. Their visibility is derived:
  - Budget screen: budgets of a deleted concept disappear and stop counting in projections.
  - Working month (Home): transactions of a deleted concept disappear and stop counting.
  - Previous months (History): transactions of a deleted concept stay visible with a faint "(deleted)" tag and keep counting.
- Records of a deleted concept cannot be edited or deleted (`410`).

### User Soft-Delete

- A soft-deleted user cannot log in, and all of their sessions are invalidated.
- Their records keep `user_id`. The username is rendered with a faint "(deleted)" tag (`user_is_deleted`).
- Their username stays reserved.

### Settings Persistence

All settings must be persisted to the database on every change. A page refresh, session re-validation, or different client must reflect the current stored values. No setting may exist only in frontend state or session memory.

---

## Database Schema (Reference)

This contract does not mandate database implementation, but the following schema satisfies all requirements:

```
users
  id              PK
  username        UNIQUE NOT NULL
  real_name       NOT NULL
  password_hash   NOT NULL
  is_admin        BOOLEAN DEFAULT false
  created_at      TIMESTAMP
  is_deleted      BOOLEAN DEFAULT false

concepts
  id              PK
  name            VARCHAR(64) NOT NULL
  flow            ENUM('in','out') NOT NULL
  created_by      FK → users.id
  created_at      TIMESTAMP
  is_deleted      BOOLEAN DEFAULT false

transactions
  id              PK
  date            DATE NOT NULL
  concept_id      FK → concepts.id
  amount          DECIMAL(10,2) NOT NULL
  user_id         FK → users.id
  created_at      TIMESTAMP
  is_deleted      BOOLEAN DEFAULT false

budgets
  id              PK
  date            DATE NOT NULL
  concept_id      FK → concepts.id
  amount          DECIMAL(10,2) NULL
  user_id         FK → users.id
  created_at      TIMESTAMP
  is_deleted      BOOLEAN DEFAULT false

settings
  id              PK
  key             VARCHAR NOT NULL
  value           TEXT NOT NULL
  user_id         FK → users.id NULLABLE
  requires_admin  BOOLEAN DEFAULT false
```

- `settings.user_id IS NULL` → global setting.
- `settings.user_id IS NOT NULL` → per-user setting.
- `transactions.amount` is always required.
- `budgets.amount` is nullable (a budget entry may exist without a reserved amount).
- No `must_change_password` column. Derived at login.
- No `type` discriminator on a unified records table. Transactions and budgets are separate tables.

---

## Endpoint Summary

| Method | Endpoint                        | Auth   | Notes                          |
|--------|---------------------------------|--------|--------------------------------|
| POST   | /api/v1/auth/login              | no     | Sets session cookie            |
| POST   | /api/v1/auth/logout             | yes    | Clears session cookie          |
| GET    | /api/v1/auth/session            | yes    | Returns current user state     |
| POST   | /api/v1/auth/password           | yes    | Only endpoint during force-change |
| GET    | /api/v1/current-month           | yes    | Month state + needs_switch     |
| POST   | /api/v1/current-month/switch    | yes    | Acknowledges month change      |
| GET    | /api/v1/settings                | yes    | Merged global + user settings  |
| PATCH  | /api/v1/settings                | yes    | Update settings                |
| GET    | /api/v1/settings/users          | admin  | List users                     |
| POST   | /api/v1/settings/users          | admin  | Create user                    |
| PATCH  | /api/v1/settings/users/:id      | admin  | Update user                    |
| DELETE | /api/v1/settings/users/:id      | admin  | Soft-delete user               |
| GET    | /api/v1/settings/concepts       | yes    | List concepts                  |
| POST   | /api/v1/settings/concepts       | yes    | Create concept                 |
| PATCH  | /api/v1/settings/concepts/:id   | yes    | Rename concept (flow immutable)|
| DELETE | /api/v1/settings/concepts/:id   | yes    | Soft-delete concept            |
| DELETE | /api/v1/settings/concepts?ids=  | yes    | Bulk soft-delete (max 100)     |
| GET    | /api/v1/records                 | yes    | List records (type + month)    |
| POST   | /api/v1/records                 | yes    | Create record                  |
| PATCH  | /api/v1/records/:id             | yes    | Update record                  |
| DELETE | /api/v1/records/:id             | yes    | Soft-delete record             |
| DELETE | /api/v1/records?type=&ids=      | yes    | Bulk soft-delete (max 100)     |
| GET    | /api/v1/projections             | yes    | Computed projections for month |

**Total: 23 endpoints.**
