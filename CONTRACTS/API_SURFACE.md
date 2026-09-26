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

HTTP status codes are still used for transport semantics (200, 201, 401, 403, 404, 409, 422, 500), but the frontend always parses the same JSON structure.

### Error Codes

| code                | HTTP | Meaning                          |
|---------------------|------|----------------------------------|
| UNAUTHORIZED        | 401  | Not authenticated                |
| FORBIDDEN           | 403  | Authenticated but not permitted  |
| PASSWORD_CHANGE_REQUIRED | 403 | Must change password before proceeding |
| NOT_FOUND           | 404  | Resource does not exist          |
| CONFLICT            | 409  | Duplicate or state conflict      |
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

### POST /api/v1/auth/logout

Clears the session cookie.

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
    "needs_switch": true
  },
  "error": null,
  "meta": null
}
```

- `current_month`: derived from server date.
- `last_acknowledged_month`: the last month the user confirmed. Stored in settings (see § settings).
- `needs_switch`: `true` when `current_month != last_acknowledged_month`.

### POST /api/v1/current-month/switch

Acknowledges the month change. Updates `last_acknowledged_month` to match `current_month`. **No data modification occurs.** No transactions are archived. No budget dates are altered. This is purely a state signal.

**Success (200):**
```json
{
  "data": {
    "current_month": "2025-07",
    "last_acknowledged_month": "2025-07",
    "needs_switch": false
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
    "last_acknowledged_month": "2025-07"
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
**Error (422):** Invalid value (e.g. currency string exceeds one grapheme cluster).

**Persistence requirement:** All settings changes must be written to the database. A page refresh must reflect the updated values. No setting may exist only in frontend state.

**Setting scopes:**

| key                      | scope    | requires_admin |
|--------------------------|----------|----------------|
| currency                 | global   | false          |
| language                 | per-user | false          |
| theme                    | per-user | false          |
| last_acknowledged_month  | per-user | false          |
| user_management          | global   | true           |

Currency changes affect all users. The frontend shows a confirmation dialog before calling this endpoint, but the backend does not enforce that confirmation.

### 3.2 User Management

All endpoints under this path require the admin role. Non-admin users receive `FORBIDDEN`.

#### GET /api/v1/settings/users

Lists all users.

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

**Error (404):** User not found.
**Error (422):** Validation failure.

#### DELETE /api/v1/settings/users/:id

Deletes a user. Hard delete. Records created by this user retain the `user_id` foreign key; the frontend displays the username as it was at creation time (or a fallback if the user no longer exists).

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
      "created_at": "2025-07-01T08:00:00Z",
      "is_deleted": false
    },
    {
      "id": 2,
      "name": "Salary",
      "flow": "in",
      "created_by": "admin",
      "created_at": "2025-07-01T08:00:00Z",
      "is_deleted": false
    }
  ],
  "error": null,
  "meta": null
}
```

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

**Error (409):** A concept with the same name and flow already exists.
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
**Error (422):** Attempting to modify `flow`, or name exceeds 64 chars.

**Renaming impact:** Renaming a concept affects all records that reference it, since records store `concept_id` and the name is resolved via the foreign key. The frontend must show a confirmation dialog before renaming.

#### DELETE /api/v1/settings/concepts/:id

**Soft-deletes** a concept. Sets `is_deleted = true`. The concept remains in the database to preserve referential integrity with historical records. Soft-deleted concepts do not appear in the concept picker for new records.

**Success (200):**
```json
{
  "data": null,
  "error": null,
  "meta": null
}
```

**Error (404):** Concept not found.

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
  "amount": 45.50,
  "user_id": 1,
  "username": "admin",
  "created_at": "2025-07-15T10:30:00Z"
}
```

- For `type: "budget"`, `amount` may be `null` (a budget entry without a reserved amount).
- For `type: "transaction"`, `amount` is always a number.
- `concept_name` and `concept_flow` are resolved from the concepts table via `concept_id`.

### GET /api/v1/records

Lists records filtered by type, month, and optional search.

**Query parameters:**

| param    | required | description                                    |
|----------|----------|------------------------------------------------|
| type     | yes      | `transaction` or `budget`                      |
| month    | yes      | `YYYY-MM` — filters by the record's `date`     |
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
**Error (422):** Validation failure (same rules as POST).

### DELETE /api/v1/records/:id

**Hard-deletes** a record. No soft delete, no undo.

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
- All budget entries (budgets persist across months; they are not filtered by month).
- All transactions in the target month.

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
- No budget dates are altered. Budget dates are informational.
- No budget amounts are reset. Budget entries persist across months.
- The only change: `last_acknowledged_month` in settings is updated to match the current month.
- The "reset" perceived by the user is natural: the new month has no transactions yet, so `actual_spend` and `actual_earn` start at zero. Budget amounts remain, so projections immediately reflect the budget baseline.
- History is simply a query for transactions in a past month. No separate storage or archiving.

### Concept Soft-Delete

- Concepts are soft-deleted (`is_deleted = true`), never hard-deleted.
- This preserves referential integrity for historical transactions and budgets.
- Soft-deleted concepts are excluded from the concept picker when creating new records.
- Soft-deleted concepts still resolve their name and flow when displaying historical records.
- To change a concept's flow, the user must delete it (soft) and create a new concept with the desired flow.

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

budgets
  id              PK
  date            DATE NOT NULL
  concept_id      FK → concepts.id
  amount          DECIMAL(10,2) NULL
  user_id         FK → users.id
  created_at      TIMESTAMP

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
| DELETE | /api/v1/settings/users/:id      | admin  | Delete user (hard)             |
| GET    | /api/v1/settings/concepts       | yes    | List concepts                  |
| POST   | /api/v1/settings/concepts       | yes    | Create concept                 |
| PATCH  | /api/v1/settings/concepts/:id   | yes    | Rename concept (flow immutable)|
| DELETE | /api/v1/settings/concepts/:id   | yes    | Soft-delete concept            |
| GET    | /api/v1/records                 | yes    | List records (type + month)    |
| POST   | /api/v1/records                 | yes    | Create record                  |
| PATCH  | /api/v1/records/:id             | yes    | Update record                  |
| DELETE | /api/v1/records/:id             | yes    | Hard-delete record             |
| GET    | /api/v1/projections             | yes    | Computed projections for month |

**Total: 21 endpoints.**
