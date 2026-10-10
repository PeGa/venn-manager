# Venn Manager — API Contract

Endpoints, shapes and errors. Behavior lives in FRONTEND.md. Rules and formulas live in BACKEND.md.

This document defines the **ports** of a hexagonal backend. The HTTP adapter implements them; the domain never knows about HTTP or JSON (AGENTS.md § Hexagonal architecture).

---

## 0. Conventions

| Topic | Rule |
|---|---|
| Base URL | `/api/v1`. The SPA and the API are served from one origin |
| Format | JSON in and out. Mutating requests must send `Content-Type: application/json`, otherwise `400 VALIDATION` |
| Auth | Session cookie, set by `POST /auth/login`. `HttpOnly`, `SameSite=Lax`, `Secure` in production. No bearer tokens |
| Household | One per deployment. Never part of a path |
| IDs | UUID v4 strings |
| Money | Integer **cents**, signed: `-8412` is −84.12. Type `Cents` below. Range `-9_999_999_999` to `9_999_999_999` |
| Dates | `YYYY-MM-DD`, household-local |
| Timestamps | ISO 8601 with offset, e.g. `2026-09-28T21:04:00+02:00` |
| Month key | `YYYY-MM` |
| Field names | camelCase |
| Success body | The resource itself. No envelope |
| Delete success | `204`, empty body |
| Error body | `{ "code": string, "message": string, "field"?: string }` (§ 11) |
| Paging | `?page=1&size=50`. `page` ≥ 1. `size` 1–200, default 50. Response `Page<T>` |
| Revision | Every successful response carries `X-Ledger-Rev: <int>` (BACKEND.md § 10) |

```ts
type UUID = string;
type Cents = number;          // integer
type ISODate = string;        // "2026-09-28"
type ISODateTime = string;    // "2026-09-28T21:04:00+02:00"
type MonthKey = string;       // "2026-09"

interface Page<T> { items: T[]; page: number; size: number; total: number; }
```

---

## 1. Shapes

### 1.1 Period

The current month in the household timezone (BACKEND.md § 3).

```ts
interface Period {
  month: MonthKey;      // "2026-09"
  start: ISODate;       // "2026-09-01"
  end: ISODate;         // "2026-09-30"
  today: ISODate;       // household-local date
  daysInMonth: number;
}
```

### 1.2 Member

```ts
interface Member {
  id: UUID;
  username: string;
  realName: string;
  initial: string;          // first character of realName, uppercased
  color: string;            // avatar tint, assigned by the server
  role: "admin" | "member";
  status: "active" | "removed";
  spentThisMonth: Cents;    // ≥ 0 (BACKEND.md § 4.5)
}
```

### 1.3 Household

```ts
interface Household {
  name: string;
  currencySign: string;       // 0–8 characters
  timezone: string;           // IANA, e.g. "Europe/Berlin"
  openingBalance: Cents;
  showMemberIncome: boolean;
  members: Member[];          // active and removed
}
```

### 1.4 Budget

A concept and its budget are one resource. The name is the concept.

```ts
interface Schedule {
  repeat: "once" | "weekly" | "biweekly" | "monthly";
  anchor: ISODate;            // first (or only) due date
}

interface Budget {
  id: UUID;
  name: string;
  amount: Cents;              // signed; persists across months
  schedule: Schedule | null;
  goal: boolean;
  createdAt: ISODateTime;
  // derived for the current period (BACKEND.md § 4.2):
  actual: Cents;
  projected: Cents;
  remaining: Cents;           // projected − actual
  over: boolean;
  overBy: Cents;              // ≥ 0
  progressPct: number;        // 0–100
}
```

### 1.5 Transaction

```ts
interface Transaction {
  id: UUID;
  budgetId: UUID;
  category: string;           // the budget's current name
  categoryDeleted: boolean;
  amount: Cents;              // signed, never 0
  memberId: UUID;
  date: ISODate;
  createdAt: ISODateTime;
  updatedAt: ISODateTime;
  archived: boolean;          // date before the current period
}
```

A transaction is read-only when `archived` or `categoryDeleted` is true.

### 1.6 Upcoming item

```ts
interface UpcomingItem {
  budgetId: UUID;
  name: string;
  dueDate: ISODate;
  amount: Cents;              // the budget amount, signed
  actual: Cents;              // signed, current period
  soon: boolean;              // overdue or due within 3 days
  overdue: boolean;
}
```

### 1.7 Forecast

```ts
interface Forecast {
  startCash: Cents;
  planned: Cents;
  transactionsNet: Cents;
  transactionCount: number;
  total: Cents;               // startCash + planned + transactionsNet
}
```

### 1.8 Activity entry

```ts
type ActivityTarget =
  | { type: "transaction"; id: UUID; archived: boolean; month: MonthKey }
  | { type: "budget"; id: UUID; goal: boolean }
  | { type: "member"; id: UUID }
  | { type: "settings"; section: "currency" | "household" | "members" | "budgets" }
  | { type: "none" };

type ActivityAction =
  | "tx.create" | "tx.update" | "tx.delete" | "tx.bulkDelete"
  | "budget.create" | "budget.rename" | "budget.amount" | "budget.schedule"
  | "budget.goal" | "budget.delete"
  | "member.invite" | "member.update" | "member.remove"
  | "settings.currency" | "settings.name" | "settings.timezone"
  | "settings.openingBalance" | "settings.memberIncome";

interface ActivityEntry {
  id: UUID;
  actorId: UUID;
  action: ActivityAction;
  params: Record<string, string | number | boolean>;
  at: ISODateTime;
  target: ActivityTarget;
}
```

`params` per action. Names are snapshots taken when the entry was written.

| Action | params |
|---|---|
| `tx.create`, `tx.update`, `tx.delete` | `category`, `amount` |
| `tx.bulkDelete` | `count` |
| `budget.create`, `budget.schedule`, `budget.delete` | `name` |
| `budget.rename` | `oldName`, `name` |
| `budget.amount` | `name`, `amount` |
| `budget.goal` | `name`, `goal` |
| `member.invite`, `member.update`, `member.remove` | `name` |
| `settings.currency` | `sign` |
| `settings.name` | `name` |
| `settings.timezone` | `timezone` |
| `settings.openingBalance` | `amount` |
| `settings.memberIncome` | `enabled` |

The target is computed when the entry is read, so it reflects the current state: a deleted transaction or a removed member yields `none`.

### 1.9 History

```ts
interface HistoryMonth {
  month: MonthKey;
  matchCount: number;         // rows matching the filters
  totalCount: number;         // rows in the month without filters
  spent: Cents;               // ≥ 0
  earned: Cents;              // ≥ 0
}

interface Breakdown {
  month: MonthKey;
  spent: Cents;
  earned: Cents;
  slices: { budgetId: UUID; category: string; amount: Cents; pct: number }[];
}

interface HistoryFacets {
  categories: { budgetId: UUID; name: string; deleted: boolean }[];
  members: Member[];
}
```

### 1.10 Balance

```ts
interface Balance {
  balance: Cents;
  monthIn: Cents;             // ≥ 0
  monthOut: Cents;            // ≥ 0
  members: { memberId: UUID; monthIn: Cents; allTimeIn: Cents }[] | null;  // null when showMemberIncome is off
}
```

### 1.11 Session

```ts
interface Session {
  member: Member;
  mustChangePassword: boolean;
  preferences: { language: "en" | "es" | null; theme: "light" | "dark" | "system" };
}
```

`language: null` means the member never picked one. The client then follows the browser (FRONTEND.md § 11.2).

---

## 2. Auth

The gate and session rules are in BACKEND.md § 8.

| Method | Path | Body | Success | Errors |
|---|---|---|---|---|
| POST | `/auth/login` | `{ username, password }` | `200 Session`, sets the cookie | `401 UNAUTHORIZED` "Invalid username or password". Same for removed members |
| POST | `/auth/logout` | — | `204`, clears the cookie, deletes the session | `401` |
| GET | `/auth/session` | — | `200 Session` | `401`, `403 PASSWORD_CHANGE_REQUIRED` |
| POST | `/auth/password` | `{ currentPassword, newPassword }` | `204` | `400 VALIDATION` (`field`: `currentPassword` when wrong, `newPassword` when outside 8–128). The new password may equal the current one |

While a session must change its password, only `POST /auth/password` and `POST /auth/logout` succeed. Every other endpoint returns `403 PASSWORD_CHANGE_REQUIRED`.

---

## 3. Me

| Method | Path | Body | Success | Errors |
|---|---|---|---|---|
| PATCH | `/me` | `Partial<{ username, realName, language, theme }>` | `200 Session` | `400 VALIDATION`, `409 DUPLICATE_NAME` (`field`: `username`) |

An empty body is `400 VALIDATION`.

---

## 4. Household

| Method | Path | Body | Success | Errors |
|---|---|---|---|---|
| GET | `/household` | — | `200 Household` | |
| PATCH | `/household` | `Partial<{ name, currencySign, timezone, openingBalance, showMemberIncome }>` | `200 Household` | `400 VALIDATION` |

Any member may patch. Each changed field writes its own activity entry.

---

## 5. Members

Writes require the admin role, otherwise `403 FORBIDDEN`. The list is part of `GET /household`.

| Method | Path | Body | Success | Errors |
|---|---|---|---|---|
| POST | `/members` | `{ username, realName, password, isAdmin }` | `201 Member` | `400 VALIDATION`, `409 DUPLICATE_NAME` |
| PATCH | `/members/{id}` | `Partial<{ realName, password, isAdmin }>` | `200 Member` | `400`, `404`, `410 GONE`, `409 LAST_ADMIN` |
| DELETE | `/members/{id}` | — | `204` | `404`, `410 GONE`, `409 LAST_ADMIN`, `409 SELF_REMOVAL` |

---

## 6. Budgets

| Method | Path | Body | Success | Errors |
|---|---|---|---|---|
| GET | `/budgets` | — | `200 { period: Period; items: Budget[] }` | |
| POST | `/budgets` | `{ name }` | `201 Budget` | `400 VALIDATION`, `409 DUPLICATE_NAME` |
| PATCH | `/budgets/{id}` | `Partial<{ name, amount, schedule, goal }>` | `200 Budget` | `400`, `404`, `410 GONE`, `409 DUPLICATE_NAME` |
| DELETE | `/budgets/{id}` | — | `204` | `404`, `410 GONE` |

- `GET` returns every non-deleted budget, goals included, in creation order.
- `POST` creates the budget with `amount: 0`, no schedule, `goal: false`.
- `PATCH amount` takes the absolute value, never a delta.
- `schedule: null` removes the schedule.

---

## 7. Transactions

| Method | Path | Body | Success | Errors |
|---|---|---|---|---|
| GET | `/transactions?page&size` | — | `200 Page<Transaction>` | |
| POST | `/transactions` | `{ budgetId, amount, date?, memberId? }` | `201 Transaction` | `400 VALIDATION`, `400 OUT_OF_PERIOD`, `410 GONE` (budget deleted) |
| PATCH | `/transactions/{id}` | `Partial<{ budgetId, amount, date, memberId }>` | `200 Transaction` | `400`, `404`, `410 GONE`, `409 READ_ONLY_HISTORY`, `409 CATEGORY_DELETED` |
| DELETE | `/transactions/{id}` | — | `204` | `404`, `410 GONE`, `409 READ_ONLY_HISTORY`, `409 CATEGORY_DELETED` |
| POST | `/transactions/bulk-delete` | `{ ids: UUID[] }` (1–500, duplicates collapsed) | `200 { deleted: UUID[]; notFound: UUID[] }` | `400`, `409 READ_ONLY_HISTORY`, `409 CATEGORY_DELETED` |

- `GET` lists the current period only, newest first: `date` descending, then `createdAt` descending. Rows whose budget was deleted are included.
- `date` defaults to today in the household timezone. It must fall inside the current period.
- `memberId` defaults to the caller. It must be an active member.
- `budgetId` must reference a non-deleted budget.
- Bulk delete is all-or-nothing for the ids it finds. Unknown or already-deleted ids go to `notFound`. If any found id is read-only, nothing is deleted and the request returns `409`.

---

## 8. Overview, upcoming, activity

| Method | Path | Success |
|---|---|---|
| GET | `/overview` | `200 Overview` |
| GET | `/upcoming` | `200 UpcomingItem[]` |
| GET | `/activity?page&size` | `200 Page<ActivityEntry>`, newest first |

```ts
interface Overview {
  period: Period;
  currencySign: string;
  forecast: Forecast;
  upcoming: UpcomingItem[];
  recentTransactions: Transaction[];   // latest 4 of the current period
  activity: ActivityEntry[];           // latest 5
}
```

---

## 9. History

Read-only. Months strictly before the current period.

Shared filters: `q` (case-insensitive substring of category name or member real name), `memberId`, `budgetId`.

| Method | Path | Success | Errors |
|---|---|---|---|
| GET | `/history/months?page&size&q&memberId&budgetId` | `200 Page<HistoryMonth>`, newest first. With filters, only months with at least one match | `400` |
| GET | `/history/months/{month}/transactions?page&size&q&memberId&budgetId` | `200 Page<Transaction>`, newest first | `400`, `404` (not a past month) |
| GET | `/history/months/{month}/breakdown?q&memberId&budgetId` | `200 Breakdown` | `400`, `404` |
| GET | `/history/facets` | `200 HistoryFacets` | |

---

## 10. Balance

| Method | Path | Success |
|---|---|---|
| GET | `/balance` | `200 Balance` |

---

## 11. Errors

```json
{ "code": "VALIDATION", "message": "Amount must not be zero", "field": "amount" }
```

`message` is plain English for logs and debugging. Clients show localized text by `code`. Messages never echo raw input, stack traces, SQL or paths.

| HTTP | code | When |
|---|---|---|
| 400 | `VALIDATION` | Bad field, unknown field, empty PATCH, wrong content type. `field` set when one field is at fault |
| 400 | `OUT_OF_PERIOD` | Transaction date outside the current period |
| 401 | `UNAUTHORIZED` | No valid session, or wrong login |
| 403 | `PASSWORD_CHANGE_REQUIRED` | Session must change its password first |
| 403 | `FORBIDDEN` | Admin-only endpoint |
| 404 | `NOT_FOUND` | Unknown id, month or route |
| 405 | `NOT_FOUND` | Unsupported method, reported as 404 |
| 409 | `DUPLICATE_NAME` | Budget name or username already used. `field` set |
| 409 | `LAST_ADMIN` | Removing or demoting the last admin |
| 409 | `SELF_REMOVAL` | An admin removing themselves |
| 409 | `READ_ONLY_HISTORY` | Changing an archived transaction |
| 409 | `CATEGORY_DELETED` | Changing a transaction whose budget was deleted |
| 410 | `GONE` | The target was soft-deleted. Message "Record not available anymore." |
| 500 | `INTERNAL` | Anything else |

---

## 12. Validation

Strings are trimmed before validation. Unknown fields are rejected.

| Field | Rule |
|---|---|
| `amount` (transaction) | Integer cents in range, ≠ 0 |
| `amount` (budget), `openingBalance` | Integer cents in range |
| budget `name` | 1–60 characters, unique among non-deleted budgets, case-insensitive |
| `schedule` | `null`, or `repeat` in the enum and `anchor` a valid date |
| `goal`, `showMemberIncome`, `isAdmin` | Boolean |
| `username` | 1–64 characters, unique among all members, removed ones included |
| `realName` | 1–128 characters |
| `password`, `newPassword` | 8–128 characters |
| household `name` | 1–60 characters |
| `currencySign` | 0–8 characters |
| `timezone` | A valid IANA zone |
| `language` | `en`, `es` |
| `theme` | `light`, `dark`, `system` |
| `date` | Valid `YYYY-MM-DD`, inside the current period |
| `ids` (bulk) | 1–500 UUIDs |
| `page`, `size` | Integers, `page` ≥ 1, `size` 1–200 |
| `q` (History) | 0–128 characters. Blank means no search |
| `month` (path) | Valid `YYYY-MM` |

---

## 13. Endpoint summary

| Method | Path | Who |
|---|---|---|
| POST | `/auth/login` | anyone |
| POST | `/auth/logout` | member, allowed during forced change |
| GET | `/auth/session` | member |
| POST | `/auth/password` | member, allowed during forced change |
| PATCH | `/me` | member |
| GET | `/household` | member |
| PATCH | `/household` | member |
| POST | `/members` | admin |
| PATCH | `/members/{id}` | admin |
| DELETE | `/members/{id}` | admin |
| GET | `/budgets` | member |
| POST | `/budgets` | member |
| PATCH | `/budgets/{id}` | member |
| DELETE | `/budgets/{id}` | member |
| GET | `/transactions` | member |
| POST | `/transactions` | member |
| PATCH | `/transactions/{id}` | member |
| DELETE | `/transactions/{id}` | member |
| POST | `/transactions/bulk-delete` | member |
| GET | `/overview` | member |
| GET | `/upcoming` | member |
| GET | `/activity` | member |
| GET | `/history/months` | member |
| GET | `/history/months/{month}/transactions` | member |
| GET | `/history/months/{month}/breakdown` | member |
| GET | `/history/facets` | member |
| GET | `/balance` | member |

**27 endpoints.**
