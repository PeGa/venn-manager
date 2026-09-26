# Venn Manager — Phase 3: Business Logic & Domain Contract

This document defines the internal rules, state transitions, and computational logic that bridge the Frontend Contract (Phase 1) and the API Contract (Phase 2). 

## 1. State & Lifecycle Mechanics

### 1.1 Soft-Delete Reality
Everything (Users, Concepts, Transactions, Budgets) uses logical deletion (`is_deleted = true`). Hard deletion is reserved for a future manual prune CLI.

**The Golden Rule of Deletion:** A record's `is_deleted` flag only ever reflects if *that specific record* was deleted. It does not reflect the state of its parent concept.

### 1.2 Concept Deletion & The "Ghost" Rule
When a user soft-deletes a Concept:
1. The Concept's `is_deleted` flips to `true`.
2. The Concept vanishes from all pickers/dropdowns.
3. **No cascade occurs.** Transactions and Budgets referencing this concept are *not* mutated. Their `is_deleted` remains `false`.

**How the UI handles Ghost Concepts:**
- **Current Month (Home/Budget):** The backend query for the current month explicitly filters out records where `concept.is_deleted = true`. The records vanish from the grid.
- **History (Past Months):** The backend query does *not* filter by concept deletion. The records remain visible. The frontend detects `concept.is_deleted = true` and renders the concept name faintly with a "(deleted)" suffix.
- **Projections:** The projection engine ignores any record where `concept.is_deleted = true`.

### 1.3 Concurrency & "Last Write Wins"
The app assumes high trust and low concurrent write volume. 
- If User A and User B edit the same record, the last `PATCH` request overwrites the first. No optimistic locking.
- If User A is editing a record, and User B deletes it (soft), User A's subsequent `PATCH` will fail.
- **Error handling:** The backend checks `is_deleted` before executing an update. If `true`, it returns HTTP 410 Gone with the message: `"Record not available anymore."`

## 2. The Projection Engine

Projections are computed on-the-fly per request. No values are cached or stored in the database.

### 2.1 Data Inclusion Rules
The engine only considers records where:
1. `record.is_deleted = false`
2. `concept.is_deleted = false`
3. The record's `date` falls within the target `month` (for transactions) or is an active budget (budgets persist, but their amounts are evaluated against the target month's transactions).

### 2.2 The Math (Per Concept)
For every concept that has at least one active budget entry:
- `budget_amount` = sum of active budget amounts for this concept (nulls treated as 0).
- `actual_amount` = sum of active transaction amounts for this concept in the target month.

**If Concept Flow is OUT (Spend):**
- Add `max(budget_amount, actual_amount)` to the total spend projection.

**If Concept Flow is IN (Earn):**
- Add `min(budget_amount, actual_amount)` to the total earn projection.

### 2.3 Unbudgeted Activity
For every active transaction in the target month where the concept has *no* active budget entries:
- If Flow is OUT, add `transaction.amount` to total spend projection.
- If Flow is IN, add `transaction.amount` to total earn projection.

### 2.4 Final Output
- `spend_projection` = total spend calculated above.
- `earn_projection` = total earn calculated above.
- `savings_projection` = `earn_projection - spend_projection`.
- `actual_spend` = sum of all active OUT transactions in the month.
- `actual_earn` = sum of all active IN transactions in the month.

## 3. Month Switch Mechanics

The month switch is a state signal, not a data mutation. 

When `POST /api/v1/current-month/switch` is called:
1. The backend updates the `last_acknowledged_month` setting for the current user to match the server's current month.
2. **No records are modified.** No transactions are archived. No budget dates are bumped. No budget amounts are reset.
3. The "reset" the user perceives is purely a side-effect of the new month having zero transactions, while the budget entries (which persist) immediately establish the new baseline for projections.

## 4. Seeding & Bootstrap

On the very first run (first migration), the database is seeded with the following baseline state to allow immediate login and configuration:

### 4.1 Users
- One user created.
- `username`: `admin`
- `real_name`: `Administrator`
- `password`: `admin` (hashed via the backend's standard password hasher, e.g., bcrypt/argon2).
- `is_admin`: `true`

### 4.2 Settings
- `currency`: `$` (global, `user_id` = null)
- `language`: `en` (global default, though users will get their own per-user setting upon creation).
- `theme`: `system` (global default).
- `last_acknowledged_month`: The current `YYYY-MM` at the time of migration.

### 4.3 Concepts
- **Empty.** The app starts with zero concepts. The admin must navigate to the Concepts screen and create them before they can add any records to the Home or Budget screens.

## 5. Validation & Edge Cases

### 5.1 Record Creation
- A transaction/budget cannot be created with a soft-deleted concept. (Backend returns 422).
- A transaction requires an `amount`. A budget allows `amount = null`.
- The `flow` is never sent by the frontend for records; it is strictly inherited from the concept. If the frontend somehow sends a mismatched flow, the backend ignores it and uses the concept's flow.

### 5.2 Concept Modification
- A concept's `flow` is immutable after creation. Attempting to `PATCH` a concept with a new `flow` returns 422.
- Renaming a concept (`PATCH` with new `name`) is allowed. Because records reference the concept via `concept_id`, the rename instantly reflects across all historical and current records without requiring a cascade update.

### 5.3 User Management
- An admin cannot delete themselves.
- An admin cannot delete the last remaining admin user.
- When a user is soft-deleted, their `is_deleted` flips to `true`. Their historical records retain the `user_id`. The frontend resolves the username and renders it faintly or with a "(deleted)" tag.
