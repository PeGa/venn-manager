# Venn Manager — Backend Contract

Domain rules and every formula. Endpoints and shapes are in API_SURFACE.md.

---

## 1. Scope

- One household per deployment. The household row always exists after seeding.
- Every figure the UI shows is computed per request from stored records. Nothing derived is stored or cached.
- Money is integer cents everywhere: database, domain, API.

---

## 2. Data model

| Table | Columns (besides `id` UUID) | Notes |
|---|---|---|
| `household` | `name`, `currency_sign`, `timezone`, `opening_balance`, `show_member_income`, `rev` | Exactly one row |
| `users` | `username` (unique), `real_name`, `password_hash`, `must_change_password`, `is_admin`, `language` (nullable), `theme`, `color`, `is_removed`, `created_at` | A member. `language` stays null until the member picks one |
| `sessions` | `token_hash` (unique), `user_id`, `created_at` | Server-side sessions |
| `budgets` | `name`, `amount`, `schedule_repeat`, `schedule_anchor`, `is_goal`, `is_deleted`, `created_by`, `created_at` | A concept and its budget |
| `transactions` | `payee`, `budget_id`, `amount`, `member_id`, `date`, `created_by`, `created_at`, `updated_at`, `is_deleted` | |
| `activity` | `actor_id`, `action`, `params` (JSON), `target_type`, `target_id`, `target_section`, `at` | |

Indexes: `transactions(date)`, `transactions(budget_id)`, `transactions(member_id)`, `budgets(name)`, `activity(at)`, `sessions(token_hash)`.

**Soft delete.** Users, budgets and transactions are never physically removed by the API. Sessions are removed on logout; they are not domain records. Activity entries are never removed.

---

## 3. Period and rollover

- **Today** is the current date in the household timezone.
- The **current period** is the calendar month containing today.
- A transaction is **archived** when its `date` is before the period start. This is derived, never stored.
- Rollover needs no job and no snapshot. When the calendar crosses into a new month, the next request computes a new period, last month's transactions become archived, and every figure follows from § 4.
- Budget amounts, schedules and goal flags persist across months. Only the calculations restart.
- Changing the timezone takes effect immediately. It only changes what "today" is.

---

## 4. Calculations

### 4.1 Counted transactions

A transaction **counts** when it is not deleted and its budget is not deleted.

Transactions of a deleted budget stay listed, as read-only rows marked `categoryDeleted`. They count nowhere: not in any total, not in past months, not in the start-of-month cash. Deleting a budget therefore changes past balances. That is intended.

### 4.2 Per budget, current period

For every non-deleted budget `b` with signed `amount`:

```
actual    = Σ amount of counted transactions of b dated inside the period

projected = max(amount, actual)   if amount > 0
          = min(amount, actual)   if amount < 0
          = actual                if amount = 0

remaining = projected − actual
over      = (amount ≠ 0) and (projected ≠ amount)
            or (amount = 0) and (actual ≠ 0)
overBy    = |actual − amount|  if over, else 0

progressPct = 0                                   if amount = 0
            = 0                                   if actual and amount have opposite signs
            = min(100, |actual| / |amount| × 100) otherwise
```

The budget is the plan. Money moved within the plan does not change the projection. Money moved beyond it replaces the plan.

### 4.3 Budget totals ("Left to spend")

Over non-deleted, **non-goal** budgets:

```
limit       = Σ −amount               over budgets with amount < 0
spent       = Σ max(0, −actual)       over budgets with amount ≤ 0
leftToSpend = limit − spent
spentPct    = 0 if limit = 0, else min(100, spent / limit × 100)
```

Goal budgets are money set aside on purpose. They count in the forecast (§ 4.4), not here.

### 4.4 Forecast

```
startCash        = opening_balance
                 + Σ amount of counted transactions dated before the period start
transactionsNet  = Σ amount of counted transactions dated inside the period
transactionCount = number of counted transactions dated inside the period
planned          = Σ remaining over every non-deleted budget, goals included
total            = startCash + planned + transactionsNet
```

Equivalently, `total = startCash + Σ projected`. Money left unspent at month end is part of the next month's `startCash`.

### 4.5 Balance and members

```
balance        = startCash + transactionsNet
monthIn        = Σ amount of counted transactions in the period with amount > 0
monthOut       = Σ −amount of counted transactions in the period with amount < 0
spentThisMonth = monthOut restricted to transactions with that member_id
member monthIn   = monthIn restricted to that member_id
member allTimeIn = Σ amount of all counted transactions of that member with amount > 0
```

`Balance.members` lists members with `allTimeIn > 0`, removed members included, ordered by `allTimeIn` descending. It is `null` when `show_member_income` is false.

### 4.6 History

For a past month, after filters:

```
matchCount = matching non-deleted transactions, counted or not
totalCount = non-deleted transactions of the month, no filters
spent      = Σ −amount of matching counted transactions with amount < 0
earned     = Σ amount of matching counted transactions with amount > 0
slices     = per budget, Σ −amount of matching counted transactions with amount < 0,
             amount descending, pct = round_half_up(slice / spent × 100)
```

Search `q` matches payee, budget name and member real name, case-insensitive. `%` and `_` in `q` are escaped, so they cannot widen the match.

Facets list every budget and every member that appears in at least one archived, non-deleted transaction.

### 4.7 Worked example

Budgets: Paycheck `+100`, Groceries `−10`, Car repair `−30`, Rent `−20`. Opening balance 0.

| Event | transactionsNet | planned | total |
|---|---|---|---|
| Month starts | 0 | +100 −10 −30 −20 = +40 | 40 |
| Groceries −5 | −5 | groceries −5 remaining → +45 | 40 |
| Groceries −25 more (−30 against −10) | −30 | groceries projected −30, remaining 0 → +50 | 20 |
| Paycheck +100 | +70 | car −30, rent −20 → −50 | 20 |
| Month ends without the car repair | — | — | next `startCash` = 70 |

Signed transactions inside one budget net out. Paycheck `+100` receiving an advance `+10`, the pay `+100` and a repayment `−10`: actual goes 10 → 110 → 100, projected 100 → 110 → 100.

---

## 5. Upcoming

For every non-deleted budget with a schedule and `amount ≠ 0`:

1. **Occurrences** inside the current period:
   - `once`: the anchor date.
   - `weekly`: every date on or after the anchor with the anchor's weekday.
   - `biweekly`: every date on or after the anchor at a multiple of 14 days from it.
   - `monthly`: the anchor's day of month, clamped to the month's last day, in every month from the anchor's month on.
2. **Done** when `actual` has reached `amount` in its direction: `actual ≥ amount` for positive amounts, `actual ≤ amount` for negative ones. Done budgets are not listed.
3. **Due date**: the first occurrence on or after today. If none remains, the last occurrence before today, marked `overdue`. Budgets with no occurrence in the period are not listed.
4. `soon` = `overdue` or due date − today ≤ 3 days.

Items are sorted by due date, then name.

---

## 6. Budgets (concepts)

- **Create**: name only. `amount 0`, no schedule, not a goal. Names are unique among non-deleted budgets, case-insensitive. The name of a deleted budget may be reused.
- **Rename**: allowed at any time. Transactions reference the budget by id, so the new name shows everywhere, past months included.
- **Amount**: absolute, signed. Persists until changed again.
- **Goal**: a flag. It moves the budget between the Budget and Goals screens and excludes it from § 4.3. Every other rule is identical.
- **Delete**: soft. The budget disappears from every list, picker, total and Upcoming. Its transactions follow § 4.1. Patching or deleting a deleted budget returns `410 GONE`.

---

## 7. Transactions

- **Create**: `amount ≠ 0`, signed as sent. `date` defaults to today and must be inside the current period. `memberId` defaults to the caller and must be active. `budgetId` must be non-deleted, otherwise `410 GONE`.
- **Update**: same rules for changed fields. Archived transactions return `409 READ_ONLY_HISTORY`. Transactions of a deleted budget return `409 CATEGORY_DELETED`. Moving a transaction to a deleted budget returns `410 GONE`.
- **Delete**: soft. Same read-only rules.
- **Bulk delete**: up to 500 distinct ids, one transaction, one activity entry (`tx.bulkDelete`). If any found id is read-only, nothing is deleted.
- Deleted transactions are never returned.

---

## 8. Members, authentication, sessions

### 8.1 Roles

- `admin` members manage member accounts. That is the only difference from `member`.
- There is always at least one active admin. Removing or demoting the last one returns `409 LAST_ADMIN`.
- An admin cannot remove themselves (`409 SELF_REMOVAL`).

### 8.2 Removal

- Sets `is_removed`. Deletes all of the member's sessions.
- The member cannot sign in. Their username stays reserved.
- Their transactions stay and keep counting.

### 8.3 Passwords

- Hashed with Argon2id (`argon2-cffi` defaults). Never returned, never logged.
- Policy: 8–128 characters. A new password may equal the current one.
- An admin may set any member's password through `PATCH /members/{id}`. That deletes all of the member's sessions.
- Changing one's own password keeps the current session and deletes the others.

### 8.4 Forced password change

A stored flag, `users.must_change_password`.

| Event | Flag |
|---|---|
| Seeded admin | set |
| Member created by an admin (`POST /members`) | set |
| Admin sets a member's password (`PATCH /members/{id}` with `password`) | set |
| Member changes their own password (`POST /auth/password`) | cleared |

While the flag is set, the member's sessions may only call `POST /auth/password` and `POST /auth/logout`. Everything else returns `403 PASSWORD_CHANGE_REQUIRED`. The member may submit the password they were given; submitting it still clears the flag.

### 8.5 Sessions

- Login creates a random token (`secrets.token_urlsafe(32)`). The cookie carries the token. The database stores only its SHA-256 hash.
- Logout deletes the session row and clears the cookie.
- Requests with an unknown token, or a token of a removed member, get `401 UNAUTHORIZED`.
- No expiry beyond logout, password changes and removal.

---

## 9. Activity

- Every successful household mutation writes one entry, except the merge case below. Login, logout, password changes and `PATCH /me` write none.
- `params` snapshot names and values at write time (API_SURFACE.md § 1.8).
- `PATCH /household` writes one entry per changed field.
- **Merge**: if the newest entry has the same actor, the same action and the same target, it is updated in place (new params, new `at`) instead of adding a row. This applies to every action.
- The target's navigational state (`archived`, `goal`, existence) is resolved when entries are read.

---

## 10. Revision

- `household.rev` starts at 1.
- Every successful household mutation, including `PATCH /me`, increments it by one in the same database transaction. Login, logout and password changes do not.
- Every successful response carries `X-Ledger-Rev` with the current value.

---

## 11. Seeding

The initial migration creates:

| Record | Values |
|---|---|
| Household | name "Hogar", currency `$`, timezone from `DEFAULT_TIMEZONE` (default `UTC`), opening balance 0, member income off, rev 1 |
| Admin | username `DEFAULT_ADMIN_USERNAME` (default `admin`), real name "Administrador", password `DEFAULT_ADMIN_PASSWORD` (default `admin`), admin, language null, theme `system` |

No budgets, no transactions. Both seeded names are user data and editable afterwards.

Members created through `POST /members` start with language null and theme `system`.

Member colors cycle through `#d9c7a8 #a9c7b6 #c9bfe0 #f0c9b8 #bcd3e6 #e6d9a3 #c5dcc0` in creation order.

---

## 12. Concurrency

- Last write wins. No version checks.
- A `PATCH` or `DELETE` on a soft-deleted target returns `410 GONE`, "Record not available anymore."
- Bulk operations and every write with an activity entry and a `rev` bump run in one database transaction.
