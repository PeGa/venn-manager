# Venn Manager — Backend Contract
## General description

Venn Manager backend (from now on called 'the backend') is a Python web service (Flask + SQLAlchemy) that provides a REST API consumed by the frontend contract [See: Venn Manager Frontend Contract]. The backend is responsible for persisting records, computing projections, enforcing authentication, and serving data in the shape the frontend expects. Nothing else.

The backend does not dictate presentation, layout, or client-side routing. It exposes endpoints, returns JSON, and enforces the business rules described in this contract. All l10n concerns are frontend-only; the backend stores and returns raw data without locale transformation. Currency symbols, language codes, and theme preferences are stored as opaque values and returned as-is.

Authentication is session-based using HTTP-only cookies. No JWT, no bearer tokens. The backend seeds a default administrator account on first run and enforces a password change before granting access to any other endpoint. All non-auth endpoints require a valid session. Authorization is binary: any authenticated user can perform any operation except user management, which is restricted to users with the administrator role.

The backend does not implement soft deletion except for `Concept` records, which require referential integrity with existing `Transaction` and `Budget` entries. All other deletions are hard removals. There is no audit trail, no undo, no versioning. Concurrency is handled with a last-write-wins policy; no optimistic locking is required.

---

## 1. Data Model

The backend persists five entities. Each entity's fields, constraints, and relationships are defined below. These are contractual obligations: the API must accept and return data consistent with these shapes.

### 1.1 User

| Field | Type | Constraints |
|-------|------|-------------|
| `id` | integer | primary key, auto-increment |
| `username` | string | required, unique |
| `real_name` | string | required |
| `password_hash` | string | required, never exposed via API |
| `is_admin` | boolean | default `false` |
| `language` | string | default `"en"`, per-user setting |
| `theme` | string | one of `"light"`, `"dark"`, `"system"`, default `"system"` |
| `must_change_password` | boolean | default `false`, set `true` on first-run seed |
| `created_at` | datetime | auto-set on creation |

- `password_hash` is never returned by any endpoint. Write-only.
- `must_change_password` is returned only by `GET /api/auth/me` and gates access to all other endpoints until resolved.
- `language` and `theme` are per-user preferences. They do not affect any other user.

### 1.2 Concept

| Field | Type | Constraints |
|-------|------|-------------|
| `id` | integer | primary key, auto-increment |
| `name` | string | required, max 64 characters |
| `flow` | string | one of `"IN"` or `"OUT"`, immutable after creation |
| `created_by` | integer | foreign key → `User.id` |
| `created_at` | datetime | auto-set on creation |
| `is_deleted` | boolean | default `false`, soft-delete flag |

- The combination of `name` + `flow` must be unique among non-deleted concepts. Two concepts may share the same `name` only if their `flow` differs, but since a concept's `flow` is immutable, this effectively means each `name` maps to exactly one active concept.
- `flow` is immutable. The API must reject any attempt to modify `flow` on an existing concept. To change a concept's flow, the frontend must delete the concept (soft delete) and create a new one [See section 3.3: Concepts].
- Deletion is soft: `is_deleted` is set to `true`. The record remains in the database to preserve referential integrity with existing `Transaction` and `Budget` entries. Soft-deleted concepts are excluded from all list endpoints but remain resolvable when referenced by existing records.

### 1.3 Transaction

| Field | Type | Constraints |
|-------|------|-------------|
| `id` | integer | primary key, auto-increment |
| `date` | date | required |
| `concept_id` | integer | foreign key → `Concept.id`, required |
| `amount` | decimal | required, precision 2, scale 2 |
| `user_id` | integer | foreign key → `User.id`, required |
| `created_at` | datetime | auto-set on creation |

- `Transaction` represents actual money movements recorded on the Home screen [See Frontend Contract, section 1: Main screen].
- `flow` is not stored on `Transaction`. It is derived from the associated `Concept.flow` at read time. The API must return `flow` as a computed field in all responses.
- `amount` is stored as a fixed-precision decimal. Floating-point arithmetic must not introduce rounding errors. The contract assumes `0.1 + 0.2 = 0.3` at all times.
- Deletion is hard. No soft delete, no tombstone.

### 1.4 Budget

| Field | Type | Constraints |
|-------|------|-------------|
| `id` | integer | primary key, auto-increment |
| `date` | date | required |
| `concept_id` | integer | foreign key → `Concept.id`, required |
| `amount` | decimal | nullable, precision 2, scale 2 |
| `user_id` | integer | foreign key → `User.id`, required |
| `created_at` | datetime | auto-set on creation |

- `Budget` represents planned money movements for the current month [See Frontend Contract, section 2: Budget].
- `amount` is nullable. An empty amount means the user has not reserved a value for that concept yet.
- `flow` is not stored on `Budget`. It is derived from the associated `Concept.flow` at read time.
- Budget records persist across month switches. They are not archived. Only their `date` fields are updated during a month switch [See section 4.2: Month Switch].
- Deletion is hard.

### 1.5 Settings

| Field | Type | Constraints |
|-------|------|-------------|
| `id` | integer | primary key, auto-increment |
| `currency` | string | required, exactly 1 grapheme cluster |

- `Settings` is a single-row table. There is exactly one settings record in the database.
- `currency` is a global setting. It affects all users. Any authenticated user may modify it [See Frontend Contract, section 5.1.5].
- `currency` must be validated as exactly one grapheme cluster. Multi-codepoint characters (such as emoji) are permitted if they render as a single visual unit. Strings like `"USD"` must be rejected.
- Language and theme are not stored here. They are per-user fields on the `User` entity.

---

## 2. Authentication & Authorization

### 2.1 Session Management

- Authentication uses server-side sessions with HTTP-only, secure cookies.
- No JWT, no bearer tokens, no API keys.
- Session expiry is managed by the server. The frontend does not handle token refresh.
- All endpoints except `POST /api/auth/login` require a valid session. Unauthenticated requests return `401 Unauthorized`.

### 2.2 First-Run Seeding

- On the first migration (or equivalent initialization), the backend seeds a default administrator account.
- The seeded account has `is_admin = true` and `must_change_password = true`.
- The default credentials are deployment-specific but must be documented for the operator.
- Until the administrator changes their password, all endpoints except `POST /api/auth/login` and `POST /api/auth/change-password` return `403 Forbidden` with a body indicating the password must be changed.

### 2.3 Authorization Rules

- Any authenticated user may perform any operation except user management.
- User management endpoints (`/api/users/*`) require `is_admin = true`. Non-admin requests to these endpoints return `403 Forbidden`.
- There are no per-record permissions. Any user may edit or delete any record, including records created by other users. This is intentional [See Frontend Contract, General description].

---

## 3. API Endpoints

All endpoints return JSON. All request bodies are JSON. All timestamps are returned in ISO 8601 format. All date fields use `YYYY-MM-DD` format.

### 3.1 Auth

#### `POST /api/auth/login`
- **Auth**: none
- **Body**: `{ "username": string, "password": string }`
- **Success**: `200 OK`, sets session cookie. Returns `{ "user": UserObject }`.
- **Failure**: `401 Unauthorized` if credentials are invalid.
- **Note**: If `must_change_password` is `true`, the response includes this flag so the frontend can redirect to a password-change flow.

#### `POST /api/auth/logout`
- **Auth**: user
- **Body**: none
- **Success**: `200 OK`, clears session cookie.
- **Failure**: `401 Unauthorized` if no valid session.

#### `GET /api/auth/me`
- **Auth**: user
- **Body**: none
- **Success**: `200 OK`. Returns `{ "user": UserObject }`.
- **UserObject** includes: `id`, `username`, `real_name`, `is_admin`, `language`, `theme`, `must_change_password`. Does not include `password_hash`.

#### `POST /api/auth/change-password`
- **Auth**: user
- **Body**: `{ "current_password": string, "new_password": string }`
- **Success**: `200 OK`. If `must_change_password` was `true`, it is set to `false`.
- **Failure**: `401 Unauthorized` if `current_password` is incorrect. `400 Bad Request` if `new_password` is missing or invalid.

### 3.2 Records (Home Screen)

These endpoints manage the actual money-movement records displayed on the Home screen [See Frontend Contract, section 1: Main screen].

#### `GET /api/records`
- **Auth**: user
- **Query params**: `month` (required, format `YYYY-MM`)
- **Success**: `200 OK`. Returns `{ "records": [TransactionObject] }`.
- **TransactionObject** includes: `id`, `date`, `concept_id`, `concept_name`, `flow`, `amount`, `user_id`, `username`, `created_at`.
- **Note**: `flow` is derived from the associated `Concept`. `concept_name` and `username` are included for display convenience. Records are sorted by `id` ascending (creation order).

#### `POST /api/records`
- **Auth**: user
- **Body**: `{ "date": string, "concept_id": integer, "amount": number }`
- **Success**: `201 Created`. Returns the created `TransactionObject`.
- **Failure**: `400 Bad Request` if `concept_id` references a soft-deleted concept, or if `amount` is not a valid decimal. `404 Not Found` if `concept_id` does not exist.
- **Note**: `flow` is not accepted in the request body. It is derived from the concept. `user_id` is derived from the authenticated session.

#### `PUT /api/records/:id`
- **Auth**: user
- **Body**: `{ "date"?: string, "concept_id"?: integer, "amount"?: number }`
- **Success**: `200 OK`. Returns the updated `TransactionObject`.
- **Failure**: `404 Not Found` if record does not exist. `400 Bad Request` for invalid values.
- **Note**: Partial updates are supported. Only provided fields are modified.

#### `DELETE /api/records/:id`
- **Auth**: user
- **Body**: none
- **Success**: `200 OK`. Returns `{ "deleted": true }`.
- **Failure**: `404 Not Found` if record does not exist.
- **Note**: Hard delete. The record is permanently removed.

#### `DELETE /api/records/bulk`
- **Auth**: user
- **Body**: `{ "ids": [integer] }`
- **Success**: `200 OK`. Returns `{ "deleted_count": integer }`.
- **Failure**: `400 Bad Request` if `ids` is empty or malformed.
- **Note**: Hard delete for all specified records. Non-existent IDs are silently ignored.

### 3.3 Concepts

These endpoints manage the accounting concepts used to categorize transactions and budget entries [See Frontend Contract, section 3: Concepts].

#### `GET /api/concepts`
- **Auth**: user
- **Query params**: none
- **Success**: `200 OK`. Returns `{ "concepts": [ConceptObject] }`.
- **ConceptObject** includes: `id`, `name`, `flow`, `created_by`, `username`, `created_at`.
- **Note**: Soft-deleted concepts are excluded. Results are sorted by `id` ascending.

#### `POST /api/concepts`
- **Auth**: user
- **Body**: `{ "name": string, "flow": string }`
- **Success**: `201 Created`. Returns the created `ConceptObject`.
- **Failure**: `400 Bad Request` if `name` exceeds 64 characters, if `flow` is not `"IN"` or `"OUT"`, or if a non-deleted concept with the same `name` and `flow` already exists.

#### `PUT /api/concepts/:id`
- **Auth**: user
- **Body**: `{ "name": string }`
- **Success**: `200 OK`. Returns the updated `ConceptObject`.
- **Failure**: `404 Not Found` if concept does not exist or is soft-deleted. `400 Bad Request` if `name` exceeds 64 characters or if the request body includes `flow`.
- **Note**: Only `name` is modifiable. Any attempt to modify `flow` must be rejected with `400 Bad Request`. To change a concept's flow, the frontend must delete the concept and create a new one.

#### `DELETE /api/concepts/:id`
- **Auth**: user
- **Body**: none
- **Success**: `200 OK`. Returns `{ "deleted": true }`.
- **Failure**: `404 Not Found` if concept does not exist or is already soft-deleted.
- **Note**: Soft delete. `is_deleted` is set to `true`. The record remains in the database.

#### `DELETE /api/concepts/bulk`
- **Auth**: user
- **Body**: `{ "ids": [integer] }`
- **Success**: `200 OK`. Returns `{ "deleted_count": integer }`.
- **Failure**: `400 Bad Request` if `ids` is empty or malformed.
- **Note**: Soft delete for all specified concepts. Non-existent or already-deleted IDs are silently ignored.

### 3.4 Budget

These endpoints manage the planned money movements for the current month [See Frontend Contract, section 2: Budget].

#### `GET /api/budget`
- **Auth**: user
- **Query params**: `month` (required, format `YYYY-MM`)
- **Success**: `200 OK`. Returns `{ "budget": [BudgetObject] }`.
- **BudgetObject** includes: `id`, `date`, `concept_id`, `concept_name`, `flow`, `amount`, `user_id`, `username`, `created_at`.
- **Note**: `flow` is derived from the associated `Concept`. `amount` may be `null`. Results are sorted by `id` ascending.

#### `POST /api/budget`
- **Auth**: user
- **Body**: `{ "date": string, "concept_id": integer, "amount": number | null }`
- **Success**: `201 Created`. Returns the created `BudgetObject`.
- **Failure**: `400 Bad Request` if `concept_id` references a soft-deleted concept. `404 Not Found` if `concept_id` does not exist.
- **Note**: `amount` is nullable. `flow` is derived from the concept. `user_id` is derived from the session.

#### `PUT /api/budget/:id`
- **Auth**: user
- **Body**: `{ "date"?: string, "concept_id"?: integer, "amount"?: number | null }`
- **Success**: `200 OK`. Returns the updated `BudgetObject`.
- **Failure**: `404 Not Found` if record does not exist. `400 Bad Request` for invalid values.
- **Note**: Partial updates are supported.

#### `DELETE /api/budget/:id`
- **Auth**: user
- **Body**: none
- **Success**: `200 OK`. Returns `{ "deleted": true }`.
- **Failure**: `404 Not Found` if record does not exist.
- **Note**: Hard delete.

#### `DELETE /api/budget/bulk`
- **Auth**: user
- **Body**: `{ "ids": [integer] }`
- **Success**: `200 OK`. Returns `{ "deleted_count": integer }`.
- **Note**: Hard delete for all specified records.

### 3.5 History

These endpoints provide read-only access to past months' transaction data [See Frontend Contract, section 4: History].

#### `GET /api/history`
- **Auth**: user
- **Query params**: `month` (required, format `YYYY-MM`)
- **Success**: `200 OK`. Returns `{ "records": [TransactionObject] }`.
- **Failure**: `400 Bad Request` if `month` is the current month or a future month. History is only available for past months.
- **Note**: Returns the same `TransactionObject` shape as `GET /api/records`. Read-only. No write operations are available for historical data.

#### `GET /api/history/months`
- **Auth**: user
- **Query params**: none
- **Success**: `200 OK`. Returns `{ "months": [string] }`, where each string is a `YYYY-MM` value representing a month that has at least one transaction record.
- **Note**: The current month is excluded from this list. Months are returned in descending order (most recent first).

### 3.6 Projections

This endpoint computes the five widget values displayed on the Home screen [See Frontend Contract, section 1.2: Widgets].

#### `GET /api/projections`
- **Auth**: user
- **Query params**: `month` (required, format `YYYY-MM`)
- **Success**: `200 OK`. Returns:
  ```json
  {
    "current_out": number,
    "current_in": number,
    "savings_projection": number,
    "spend_projection": number,
    "earn_projection": number
  }
  ```
- **Note**: All values are computed according to the business logic rules in section 4.1. Values are returned as fixed-precision decimals serialized to two decimal places.

### 3.7 Month Switch

These endpoints handle the detection and confirmation of a new month [See Frontend Contract, section 2: Budget, month switch].

#### `GET /api/month/status`
- **Auth**: user
- **Query params**: none
- **Success**: `200 OK`. Returns:
  ```json
  {
    "current_month": string,
    "active_month": string,
    "switch_available": boolean
  }
  ```
- **Note**: `current_month` is the server's current `YYYY-MM`. `active_month` is the month the app is currently operating in (the month of the most recent transactions or the last confirmed switch). `switch_available` is `true` if `current_month > active_month`.

#### `POST /api/month/switch`
- **Auth**: user
- **Body**: none
- **Success**: `200 OK`. Returns `{ "switched": true, "new_month": string }`.
- **Failure**: `400 Bad Request` if no switch is available.
- **Note**: This endpoint triggers the month-switch logic described in section 4.2. All budget entry dates are updated to the new month. The previous month's transactions become accessible via `/api/history`.

### 3.8 Settings

These endpoints manage global and per-user configuration [See Frontend Contract, section 5: Configuration].

#### `GET /api/settings`
- **Auth**: user
- **Query params**: none
- **Success**: `200 OK`. Returns:
  ```json
  {
    "currency": string,
    "language": string,
    "theme": string
  }
  ```
- **Note**: `currency` is the global setting. `language` and `theme` are the authenticated user's personal settings.

#### `PUT /api/settings/currency`
- **Auth**: user
- **Body**: `{ "currency": string }`
- **Success**: `200 OK`. Returns `{ "currency": string }`.
- **Failure**: `400 Bad Request` if `currency` is not exactly one grapheme cluster.
- **Note**: This is a global setting. Any authenticated user may modify it. The frontend is responsible for displaying a confirmation dialog before calling this endpoint [See Frontend Contract, section 5.1.5].

#### `PUT /api/settings/language`
- **Auth**: user
- **Body**: `{ "language": string }`
- **Success**: `200 OK`. Returns `{ "language": string }`.
- **Note**: Per-user setting. Does not affect other users.

#### `PUT /api/settings/theme`
- **Auth**: user
- **Body**: `{ "theme": string }`
- **Success**: `200 OK`. Returns `{ "theme": string }`.
- **Failure**: `400 Bad Request` if `theme` is not one of `"light"`, `"dark"`, `"system"`.
- **Note**: Per-user setting.

### 3.9 User Management (Admin Only)

These endpoints are restricted to users with `is_admin = true`. All requests from non-admin users return `403 Forbidden`.

#### `GET /api/users`
- **Auth**: admin
- **Query params**: none
- **Success**: `200 OK`. Returns `{ "users": [UserObject] }`.
- **UserObject** includes: `id`, `username`, `real_name`, `is_admin`, `language`, `theme`, `created_at`. Does not include `password_hash` or `must_change_password`.

#### `POST /api/users`
- **Auth**: admin
- **Body**: `{ "username": string, "real_name": string, "password": string, "is_admin": boolean }`
- **Success**: `201 Created`. Returns the created `UserObject`.
- **Failure**: `400 Bad Request` if `username` already exists or if required fields are missing.
- **Note**: Newly created users have `must_change_password = false`. Only the first-run seeded admin has `must_change_password = true`.

#### `PUT /api/users/:id`
- **Auth**: admin
- **Body**: `{ "username"?: string, "real_name"?: string, "password"?: string, "is_admin"?: boolean }`
- **Success**: `200 OK`. Returns the updated `UserObject`.
- **Failure**: `404 Not Found` if user does not exist. `400 Bad Request` for invalid values.
- **Note**: Partial updates are supported. If `password` is provided, it is updated. An admin may modify any user's record, including their own.

#### `DELETE /api/users/:id`
- **Auth**: admin
- **Body**: none
- **Success**: `200 OK`. Returns `{ "deleted": true }`.
- **Failure**: `404 Not Found` if user does not exist. `400 Bad Request` if attempting to delete the last remaining admin user.
- **Note**: Hard delete. The backend must prevent deletion of the last admin to avoid locking out all administrative access.

---

## 4. Business Logic

### 4.1 Projection Calculations

The projections endpoint [See section 3.6] computes five values. The calculations are defined below and must be followed exactly.

**Definitions:**
- Let `B` be the set of `Budget` records for the given month where `amount` is not null.
- Let `T` be the set of `Transaction` records for the given month.
- For each concept `c` in `B`, let `budget_amount(c)` be the budget's amount.
- For each concept `c`, let `actual_amount(c)` be the sum of `Transaction.amount` for all transactions in `T` with the same `concept_id`.
- Let `unbudgeted` be the set of transactions in `T` whose `concept_id` does not appear in `B`.

**Spend Projection** (`flow = "OUT"`):
```
spend_projection =
    sum( max(budget_amount(c), actual_amount(c)) for c in B where flow(c) = "OUT" )
  + sum( t.amount for t in unbudgeted where flow(t) = "OUT" )
```
This is a pessimistic projection: if actual spending exceeds the budget, the actual value replaces the budgeted value.

**Earn Projection** (`flow = "IN"`):
```
earn_projection =
    sum( min(budget_amount(c), actual_amount(c)) for c in B where flow(c) = "IN" )
  + sum( t.amount for t in unbudgeted where flow(t) = "IN" )
```
This is a pessimistic projection: if actual earnings are below the budget, the actual value replaces the budgeted value.

**Current Out** (actual spending so far):
```
current_out = sum( t.amount for t in T where flow(t) = "OUT" )
```

**Current In** (actual earnings so far):
```
current_in = sum( t.amount for t in T where flow(t) = "IN" )
```

**Savings Projection**:
```
savings_projection = earn_projection - spend_projection
```

All values are computed using fixed-precision decimal arithmetic. Floating-point rounding errors are not acceptable.

### 4.2 Month Switch

When `POST /api/month/switch` is called and a switch is available:

1. Determine the new month (the server's current `YYYY-MM`).
2. For every `Budget` record:
   - Update `date` to the same day in the new month.
   - If the day exceeds the new month's last day, clamp to the last day. Examples: January 31 → February 28 (or 29 in leap years). March 31 → April 30.
3. The previous month's `Transaction` records remain in the database unchanged. They become accessible via `GET /api/history` with the previous month's `YYYY-MM` value.
4. Budget records are not archived, duplicated, or reset. They persist with updated dates.
5. The `active_month` is updated to the new month.

This operation is idempotent. Calling it multiple times when no switch is available returns `400 Bad Request` and makes no changes.

### 4.3 Concept Constraints

- A concept's `flow` is immutable after creation. The `PUT /api/concepts/:id` endpoint must reject any request body containing a `flow` field.
- When a concept is soft-deleted, existing `Transaction` and `Budget` records referencing that concept remain valid. The concept's `name` and `flow` must still be resolvable for display purposes.
- Creating a new concept with the same `name` as a soft-deleted concept is permitted, provided the `flow` does not conflict with any active (non-deleted) concept.

---

## 5. Error Handling

All error responses follow a consistent shape:

```json
{
  "error": string,
  "detail": string
}
```

- `error` is a short, machine-readable error code (e.g., `"UNAUTHORIZED"`, `"NOT_FOUND"`, `"VALIDATION_ERROR"`).
- `detail` is a human-readable description of the problem.

Standard HTTP status codes are used:
- `400 Bad Request`: validation errors, malformed input.
- `401 Unauthorized`: missing or invalid session.
- `403 Forbidden`: authenticated but insufficient permissions (e.g., non-admin accessing user management, or `must_change_password` not yet resolved).
- `404 Not Found`: resource does not exist.
- `409 Conflict`: uniqueness constraint violation (e.g., duplicate username, duplicate concept).
- `500 Internal Server Error`: unexpected server failure. The response must not leak stack traces or internal details.

---

## Appendix

These clarifications apply to the entire backend contract.

- This is a CONTRACT for the BACKEND. It defines API behavior, data shapes, and business rules. It does not prescribe framework-specific implementation details, ORM patterns, or file structure. Flask and SQLAlchemy are the chosen tools, but this contract describes what the system must do, not how the code must be organized.
- All list endpoints return results sorted by `id` ascending (creation order). No pagination is required for the expected data volume. If pagination is added later, it must not alter the default sort order.
- All list endpoints support substring filtering via a `filter` query parameter. The filter applies to relevant text fields (`concept_name`, `username`). Filtering must respect month boundaries: a filter on a given month must not return results from a different month.
- All amounts are represented as JSON numbers with exactly two decimal places. The value `0` is serialized as `0.00`.
- Dates are serialized as `YYYY-MM-DD` strings. Datetimes are serialized as ISO 8601 strings.
- The backend does not perform l10n, currency conversion, or locale-aware number formatting. All values are returned raw. The frontend handles display formatting.
- There is no rate limiting, no request throttling, and no audit logging. These are not on the roadmap.
- Data export (CSV, JSON backup) is not planned.
- WebSocket or server-sent events are not planned. The frontend polls `GET /api/month/status` to detect month changes.
- The `Settings` table contains exactly one row. If the row does not exist, the backend must create it with a default `currency` value (e.g., `"$"`) on first access.
- On floating-point precision: the backend must use fixed-precision decimal types. The contract assumes `0.1 + 0.2 = 0.3` at all times. Any deviation is a contract violation.
- Concurrency: last write wins. No optimistic locking, no conflict detection. If two users edit the same record simultaneously, the last `PUT` request determines the final state.
- The `must_change_password` flag is enforced server-side. The frontend may redirect the user, but the backend must independently reject requests until the password is changed.