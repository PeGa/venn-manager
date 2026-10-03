# Venn Manager — Frontend Contract

This contract defines what the user sees and does, and which actions reach the backend.
It covers the web and mobile layouts, which come from one codebase.

| Document | Role |
|---|---|
| `CONTRACTS/FRONTEND.md` | Behavior, screens, interactions, requests. This file. |
| `CONTRACTS/API_SURFACE.md` | Endpoints, shapes, errors. |
| `CONTRACTS/BACKEND.md` | Domain rules and every formula. |
| `frontend/src/styles/index.css` | Visual reference: the design tokens for colors, type, spacing, radii, shadows. |

The design tokens are the visual reference. Where they disagree with this contract, this contract wins.

---

## 1. Product rules

- One household per deployment. Every member sees and edits the same ledger.
- Concepts are names. Every concept has exactly one budget, which holds a signed amount.
- Every transaction belongs to a budget. Its amount is signed as the user typed it.
  Positive money comes in. Negative money goes out. There is no "flow" field anywhere.
- The currency sign is a display label. No conversion. No locale number formatting.
- Months roll over on their own. Past months appear in History and are read-only.
- The activity feed is informational. It is not an audit trail.

The formulas behind every figure are in BACKEND.md § 4. The client shows server values.

---

## 2. One system, two layouts

Two independent switches drive presentation. Data and requests never differ.

### 2.1 Viewport width decides layout

| | Wide (≥ 768 px) | Narrow (< 768 px) |
|---|---|---|
| Navigation | Fixed left sidebar, 210 px | Title bar with a 44×44 menu button. The menu opens as a dropdown panel over the content |
| Sidebar / title bar content | Brand "Venn Manager", household name · member count, nav items, sync and "Signed in as" card at the bottom | Screen title on the left, sync chip top right, menu button |
| Screen header | Month label ("September 2026") above the screen title | Screen title only |
| Grids | Overview 1.1fr / 1fr. Budget and Goals 2 columns. Settings 3 columns | One column |
| Card copy | Full | Compact (noted per screen) |

### 2.2 Pointer type decides interaction

Detected with the media query `(pointer: coarse)`, not with width.

| | Fine pointer (mouse, trackpad) | Coarse pointer (touch) |
|---|---|---|
| Transaction selection | Click, Ctrl/⌘+click, Shift+click (§ 6.1) | Tap menu, long-press select mode (§ 6.2) |
| Transaction edit | Inline edit bar | Bottom sheet |
| Dialogs | Centered modal | Bottom sheet |
| Hover states | Yes | No |

A narrow desktop window keeps mouse selection. A tablet in landscape gets the sidebar and touch interactions.

### 2.3 Navigation

Order: **Overview, Budget, Transactions, History, Goals, Balance, Settings.**

- Selecting an item switches the screen instantly and closes the narrow menu.
- The narrow menu also closes on Escape or on a tap outside it.
- The menu's last entry is "Signed in as {real name}", which opens Profile (§ 5.8).
- On wide layouts the sidebar's bottom card shows the sync chip and "Signed in as {real name}". Clicking it opens Profile.

### 2.4 Sync chip

- Shows `● SYNCED · rev {n}`, where `n` is the latest `X-Ledger-Rev` seen (API_SURFACE.md § 0).
- When the latest request failed for network reasons it shows `● NOT SYNCED` in coral until a request succeeds.

---

## 3. Authentication screens

Rules come from API_SURFACE.md § 2 and BACKEND.md § 8. Screens use the design's visual language: a single centered card on the ground color.

### 3.1 Sign in

- Fields: Username, Password. Button: Sign in.
- Shown in the browser's language (§ 11.2), since no user is known yet.
- Invalid credentials show "Invalid username or password" under the form.
- No registration and no password recovery.

### 3.2 Forced password change

- Shown when the session reports `mustChangePassword`, or when any request returns `PASSWORD_CHANGE_REQUIRED`.
- Fields: Current password, New password, Repeat new password. Button: Change password.
- A Log out button is always available on this screen.
- New password rules: 8–128 characters, both new fields equal. Keeping the assigned password is allowed. Errors show inline next to the field.

---

## 4. Shared elements

### 4.1 Transaction row

Used on Overview links, Transactions and History.

| Part | Content |
|---|---|
| Avatar | Member initial on the member's color |
| Title | Payee |
| Subtitle | Member real name · date (§ 9.2) |
| Category | Budget name |
| Amount | Signed, two decimals (§ 9.1). Positive amounts in accent green with a leading `+` |

- A transaction whose budget was deleted is dimmed. Its category reads "{name} (deleted)". It cannot be selected, edited or removed.
- A transaction by a removed member keeps the member's name, dimmed, with "(removed)".

### 4.2 Budget card

Used on Budget and Goals.

| Part | Content |
|---|---|
| Title | Budget name |
| Period label | Current period, e.g. `SEP 1–30` |
| Due chip | Schedule summary: "No due date", "Once · Sep 15", "Weekly · Mondays", "Every 2 weeks · from Sep 3", "Monthly · 1st". Opens the schedule dialog (§ 4.3) |
| Goal tick | Checkbox labelled "Goal" |
| Stepper | `−` button, currency sign, amount input, `+` button |
| Progress bar | `progressPct` from the server. Bar green normally, coral when `over` |
| Note | See below |

**Stepper.**
- The input shows the signed budget amount without the currency sign, e.g. `-800` or `2240`.
- `+` adds 50.00 to the signed value. `−` subtracts 50.00. The arithmetic is literal: on `-800`, `+` gives `-750`.
- Typed values are accepted on Enter, on blur, or 400 ms after the last keystroke.
- An unparseable value reverts to the last saved amount.
- The client sends the resulting absolute amount (`PATCH /budgets/{id}`). While the write is pending, the card recomputes its note and bar locally with BACKEND.md § 4.2.

**Note.** Figures are whole currency units (§ 9.1). `actual` and `amount` are signed; the note shows absolute values.

| Budget amount | State | Note |
|---|---|---|
| Negative | not over | `{actual} spent · {remaining} left` |
| Negative | over | `{actual} spent · {overBy} over` (coral) |
| Positive | not over | `{actual} received · {remaining} to go` |
| Positive | over | `{actual} received · {overBy} above` |
| Zero | no transactions | `{currency}0 · Set an amount` |
| Zero | with transactions | `{actual} spent` or `{actual} received` by the sign of `actual`, then `· Set an amount` (coral) |

On goal budgets the words change: `{actual} of {amount} · {remaining} to go`, `Reached` when `remaining` is zero and not over, `{overBy} over` when over.

**Goal tick.** Toggling it sends `PATCH /budgets/{id}` with `goal`. A goal budget leaves the Budget screen and appears on Goals. Unticking moves it back.

### 4.3 Schedule dialog

- Repeat: None, Once, Weekly, Every 2 weeks, Monthly.
- Date: a native date input. Required unless Repeat is None.
  - Once: the due date.
  - Weekly: the first due date; the weekday repeats.
  - Every 2 weeks: the first due date; repeats every 14 days.
  - Monthly: the first due date; the day of month repeats, clamped to short months.
- Buttons: Cancel, Save. Save sends `PATCH /budgets/{id}` with `schedule`.

### 4.4 Dialogs and sheets

- Modal on fine pointers, bottom sheet on coarse pointers (§ 2.2).
- Scrim `rgba(30,29,26,.38)`. Close on Escape, on the scrim, or on Cancel.
- Focus moves into the dialog on open and returns to the trigger on close.

### 4.5 Confirmations

A confirmation dialog appears before:

| Action | Text |
|---|---|
| Removing more than one transaction | "Remove {n} transactions?" |
| Removing a budget concept | "Remove {name}? Its budget disappears. Its transactions stay visible, marked (deleted), and stop counting in every total, past months included." |
| Removing a member | "Remove {name}? They can no longer sign in. Their transactions stay." |

Removing a single transaction happens immediately, with no confirmation.

---

## 5. Screens

### 5.1 Overview

Wide: two columns. Left: hero, Recent activity. Right: Month-end forecast, Coming up.
Narrow order: hero, forecast, Coming up, Recent activity.

**Hero "Left to spend this month"** (narrow: "Left to spend").
- Figure: `budgetTotals.leftToSpend`, whole units, 46 px mono (narrow 36 px). Can be negative.
- Bar: `budgetTotals.spentPct`.
- Line: "{spent} of {limit} budgeted · all members combined" (narrow: "{spent} of {limit}").
- Goal budgets do not count here (BACKEND.md § 4.3).

**Recent activity.**
- The latest 5 entries. Caption "last 5 actions" (wide only).
- Row: actor avatar, **actor name** + sentence (§ 7.1), then "{when} · {section}", then a chevron.
- Hover background `#f4f1ea` on fine pointers.
- Clicking a row navigates to its target and highlights it (§ 7.2). An entry whose target is `none` has no chevron and does nothing.

**Month-end forecast.**
- Wide: title "Month-end forecast", subtitle "Recomputed on every transaction", then three lines:

  | Line | Value |
  |---|---|
  | Start-of-month cash | `forecast.startCash` |
  | Planned (still to move) | `forecast.planned`, with sign |
  | Logged transactions ({transactionCount}) | `forecast.transactionsNet`, with sign |

  Then "Forecast total" with `forecast.total` (30 px mono), then the formula chip:
  `{startCash} + {planned} + {transactionsNet} = {total}`. A negative term is written with `−` instead of `+`.
- Narrow: title "Forecast", the total, and the formula chip.
- All forecast figures use two decimals.

**Coming up.**
- Items from `upcoming`, already sorted by the server.
- Row: date chip (month abbreviation over day), budget name, status line, amount.
- Status line: "Overdue", "Due today", "Due tomorrow", or "Due in {n} days".
- Amount: "{actual} of {amount}", absolute values, whole units.
- When `soon` is true the date chip uses tint `#f6dcd3` and the status line uses coral text `#a4432a`.
- Header link "All bills" opens Budget.
- Empty: "Nothing scheduled this month."

### 5.2 Budget

- Budget cards (§ 4.2) for every non-goal budget, in creation order. Two columns wide, one narrow.
- A trailing dashed card "+ Add budget concept in Settings" opens Settings and highlights the Budget concepts card.
- With no budgets, only the dashed card shows.

### 5.3 Transactions

**Add bar.**
- Fields: Payee, Amount, Category button, Add button (wide label "Add", narrow label "+").
- Amount is literal: `25` records +25.00, `-25` records −25.00 (§ 9.3 parsing).
- Category button cycles through all non-deleted budgets in creation order, goals included. The first budget is preselected.
- Add is disabled until the amount parses to a non-zero value.
- Enter in Payee or Amount submits.
- An empty payee is sent as "Untitled".
- After a successful add, Payee and Amount clear. The category stays.
- With no budgets, the bar is replaced by "Add a budget concept in Settings to start logging", linking to Settings.
- The date is always today in the household's timezone. The add bar has no date field.

**List.**
- Current period only, newest first, transaction rows (§ 4.1).
- 200 per page. A "Show more" button appears when more exist.
- Empty: "No transactions this month yet."

**Selection, edit, remove.** See § 6. Edit changes payee, amount and category. The amount field shows the signed value and saves literally.

### 5.4 History

Read-only. Months before the current period, newest first.

**Filters.**
- Search input "Search payee, category or member". Debounced 300 ms.
- Member chips: "All" plus every member in `facets.members`.
- Category chips: "All" plus every category in `facets.categories`. Deleted categories read "{name} (deleted)".
- "Clear" resets all three. It is coral when any filter is active, faint otherwise.
- Filters are UI state. They are not persisted and reset on reload.
- Every filter change refetches; filtering happens on the server.

**Month group.**
- Header: month label ("August 2026"), count, "Spent {spent}", "Earned {earned}", "Details…" button.
- Count: "{n} transactions", or "{matchCount} of {totalCount} transactions" when filters hide some.
- Rows: transaction rows (§ 4.1), no selection.
- Months load 12 per page. "Show earlier months" loads the next page.
- Each month's rows load with that month, 200 per page, with "Show more" inside the group.

**Details.**
- Opens a dialog (§ 4.4) titled with the month label.
- Line: "Spent {spent} · Earned {earned}".
- Pie chart of `breakdown.slices`, colors in the pie palette order.
- Legend rows: color swatch, category, amount, percentage.
- Totals and the pie respect active filters.

**Empty states.**
- No past months at all: "Nothing here yet. Months move here when they end."
- Filters match nothing: "No transactions match these filters."

### 5.5 Goals

- Budget cards (§ 4.2, goal wording) for every goal budget, in creation order.
- Empty: "Tick Goal on a budget to track it here." with a link to Budget.

### 5.6 Balance

Nav label "Balance". Screen title "Household balance".

- Hero: `balance.balance`, two decimals. Line: "In {monthIn} · Out {monthOut} this month".
- When the household setting `showMemberIncome` is on, a card "What each member brings in" lists members with income: avatar, name, "{monthIn} this month", "{allTimeIn} all time". Removed members appear dimmed with "(removed)".
- When the setting is off, only the hero shows.

### 5.7 Settings

Household-wide. Every member can edit everything here except member accounts, which are admin-only.

**Currency sign.**
- Subtitle "Display only. Any symbol or code."
- Text input, 0–8 characters, saved 400 ms after the last keystroke.
- Quick chips `$ € £ ¥` set the value immediately. The chip matching the current value is filled.

**Household.**
- Name. Saved on blur or Enter.
- Timezone: a select of IANA zones (`Intl.supportedValuesOf('timeZone')`). Saved on change.
- Opening balance: signed amount, two decimals. Saved on blur or Enter. Hint: "What the household had before using Venn Manager."
- Toggle "Show what each member brings in", hint "Adds a per-member total of logged income to Balance." Saved on change.

**Members.**
- Subtitle "Everyone shares one ledger and can edit budgets."
- Rows for active members: avatar, real name, "{role} · {spentThisMonth} spent". Role reads "Admin" or "Member".
- Admins also see:
  - A Remove button on every row except their own (confirmation, § 4.5).
  - Clicking a row opens the account dialog: Real name, Admin toggle, New password (optional), Save, Cancel.
  - An input "Name to invite" and an Invite button. Invite opens the invite dialog with Real name prefilled, plus Username, Initial password, Admin toggle, Cancel, Invite.
- Non-admins see the rows only.
- Server errors (`DUPLICATE_NAME`, `LAST_ADMIN`, `SELF_REMOVAL`, `VALIDATION`) show inline in the dialog.

**Budget concepts.**
- Subtitle "Added concepts appear in Budget; set the amount there."
- One row per non-deleted budget, in creation order, goals included.
- Clicking a name turns it into an input. Enter or blur saves the rename. Escape cancels.
- `×` removes, after confirmation (§ 4.5).
- Input "e.g. Pets" and an Add button. Trimmed empty names do nothing. A duplicate name (case-insensitive) shows "That name is already used" inline.

### 5.8 Profile

Per user. Reached from "Signed in as" (§ 2.3). Not part of the nav list.

- **Account:** Real name, Username. Saved on blur or Enter. A taken username shows inline.
- **Password:** Current password, New password, Repeat new password, Change password. Rules as § 3.2.
- **Preferences:** Language chips (English, Español). Theme chips (Light, Dark, System). Saved on click.
- **Sign out** button.

---

## 6. Selection model

### 6.1 Fine pointer

- Click selects one row and sets it as the anchor.
- Ctrl/⌘+click toggles a row and sets it as the anchor.
- Shift+click selects the contiguous range from the anchor to the clicked row.
- Selected rows use background `#dcebe1`.
- Below the list: "Edit selected" (enabled only with exactly one row), "Remove selected" (enabled with one or more), and a hint: "Click a row to select · Ctrl/⌘ for several · Shift for a range", replaced by "{n} selected" when rows are selected.
- Disabled buttons use background `#eeebe4` and text `#a9a49a`.
- Edit opens the inline edit bar: Payee, Amount, Category button (cycles like the add bar), Save, Cancel.
- Opening the edit bar or changing the selection closes any open edit bar.

### 6.2 Coarse pointer

- Tap on a row, outside select mode, opens the action sheet: title (payee), Edit, Remove, Cancel.
- Long-press (450 ms) enters select mode and selects the row. Rows show `✓` instead of the avatar.
- In select mode a tap toggles a row. A top bar shows "{n} selected", Remove, Done.
- Long-press on a selected row opens the action sheet titled "{n} selected". Edit is disabled when more than one row is selected. Remove reads "Remove {n} transactions".
- Edit opens the edit sheet: Payee, Amount, category chips, Cancel, Save.
- Done or an empty selection leaves select mode.

### 6.3 Remove

- One transaction: removed immediately.
- More than one: confirmation (§ 4.5), then one bulk request.

---

## 7. Activity and highlight

### 7.1 Sentences

The server sends an action and its parameters (API_SURFACE.md § 1.8). The client builds the sentence from localized templates. English templates:

| Action | Sentence |
|---|---|
| `tx.create` | added “{payee}” |
| `tx.update` | edited “{payee}” |
| `tx.delete` | removed “{payee}” |
| `tx.bulkDelete` | removed {count} transactions |
| `budget.create` | added the {name} budget |
| `budget.rename` | renamed {oldName} to {name} |
| `budget.amount` | set the {name} budget to {amount} |
| `budget.schedule` | changed when {name} is due |
| `budget.goal` | made {name} a goal / moved {name} back to Budget |
| `budget.delete` | removed the {name} budget |
| `member.invite` | added {name} to the household |
| `member.update` | updated {name}'s account |
| `member.remove` | removed {name} from the household |
| `settings.currency` | changed the currency sign to {sign} (or "removed the currency sign" when empty) |
| `settings.name` | renamed the household to {name} |
| `settings.timezone` | changed the timezone to {timezone} |
| `settings.openingBalance` | set the opening balance to {amount} |
| `settings.memberIncome` | turned member income on / off |

`{amount}` is formatted with § 9.1, whole units for budgets, two decimals for the opening balance.

Section labels after the time: Transactions, History, Budget, Goals, Settings.

### 7.2 Navigation and highlight

| Target | Destination |
|---|---|
| Transaction, not archived | Transactions |
| Transaction, archived | History. Filters clear. The month containing it loads and scrolls into view |
| Budget, not goal | Budget |
| Budget, goal | Goals |
| Member | Settings › Members row |
| Settings section | Settings › that card |
| None | Not clickable |

- The destination element scrolls into view and is highlighted: background `#eef4ef`, border `#2f6b4f`, for 3.5 s.
- If the target no longer exists the screen opens without a highlight.

---

## 8. Data loading

- Each screen fetches its data every time it opens and when the window regains focus.
- Cached data paints immediately while the refetch runs. The first load shows card skeletons.
- After the user's own mutation, the screen applies the returned record and refetches what changed. Other members' edits appear on the next fetch. Last write wins.
- When a response's `period.month` differs from the cached one, every cached query is dropped and the current screen refetches. That is how the client notices a month rollover.
- Failed network requests retry up to 3 times. Then the card shows "Couldn't load this. Retry".

### 8.1 Errors

- `UNAUTHORIZED` → Sign in screen.
- `PASSWORD_CHANGE_REQUIRED` → forced password change screen.
- `VALIDATION`, `DUPLICATE_NAME` with `field` → inline message next to that field.
- `GONE`, `READ_ONLY_HISTORY`, `CATEGORY_DELETED` → a dismissible notice at the top of the screen ("Record not available anymore." or "This transaction can't be changed."), then refetch.
- Anything else → "Something went wrong. Try again." notice.
- Messages are localized by code. Raw codes and server text are never shown.

---

## 9. Formatting

### 9.1 Money

Amounts travel as integer cents (API_SURFACE.md § 0).

- Format: `sign + currencySign + digits`.
  - `sign` is `−` (U+2212) for negatives. With the "signed" option, positives get `+`.
  - `digits` use `,` for thousands and `.` for decimals, in every language.
  - Example: `−$1,629`, `+$2,240.00`, `$0.00`.
- Two decimals: transaction amounts, forecast lines and formula, balance figures, opening balance.
- Whole units (rounded half up): hero, budget notes and totals, Coming up, History totals and pie legend, member spend.
- The currency sign may be empty.

### 9.2 Dates and times

| Value | English | Spanish |
|---|---|---|
| Transaction date | "Today", "Yesterday", otherwise "Sep 26" | "Hoy", "Ayer", otherwise "26 sept" |
| Activity time | "Just now" (under 5 minutes), "Today", "Yesterday", otherwise "Sep 26" | "Ahora mismo", "Hoy", "Ayer", otherwise "26 sept" |
| Period label | "SEP 1–30" | "1–30 SEPT" |
| Screen header month | "September 2026" | "Septiembre 2026" |
| History month | "August 2026" | "Agosto 2026" |
| Due chip, monthly | "Monthly · 1st" | "Mensual · día 1" |
| Due chip, weekly | "Weekly · Mondays" | "Semanal · lunes" |

- "Today" is the household's local date, from `period`.
- Month and weekday names come from `Intl.DateTimeFormat` in the user's language. Word order, capitalization and ordinals come from templates in the locale files.
- Every date in the screens above uses these formats. The English examples elsewhere in this contract are illustrations.

### 9.3 Amount input parsing

- Spaces are ignored.
- An optional leading `+`, `-` or `−`.
- Digits with an optional decimal separator, `.` or `,`, followed by at most two digits.
- No thousands separators.
- The result is converted to integer cents. Anything else is invalid.

---

## 10. Requests

Only the actions listed here reach the backend. Navigation, selection, highlights, menus, edit drafts and filter typing (before the debounce) never do.

| Trigger | Request |
|---|---|
| App start | `GET /auth/session`, then `GET /household` |
| Sign in | `POST /auth/login` |
| Change password | `POST /auth/password` |
| Sign out | `POST /auth/logout` |
| Open Overview | `GET /overview` |
| Open Budget or Goals | `GET /budgets` |
| Budget stepper, typed amount | `PATCH /budgets/{id}` `{ amount }` |
| Goal tick | `PATCH /budgets/{id}` `{ goal }` |
| Schedule dialog Save | `PATCH /budgets/{id}` `{ schedule }` |
| Open Transactions | `GET /transactions`, `GET /budgets` |
| Add | `POST /transactions` |
| Edit Save | `PATCH /transactions/{id}` |
| Remove one | `DELETE /transactions/{id}` |
| Remove several | `POST /transactions/bulk-delete` |
| Open History | `GET /history/facets`, `GET /history/months` |
| History filter change | `GET /history/months` with filters |
| Month group loads | `GET /history/months/{month}/transactions` |
| Details… | `GET /history/months/{month}/breakdown` |
| Open Balance | `GET /balance` |
| Open Settings | `GET /household`, `GET /budgets` |
| Currency, household fields, toggle | `PATCH /household` |
| Add concept | `POST /budgets` `{ name }` |
| Rename concept | `PATCH /budgets/{id}` `{ name }` |
| Remove concept | `DELETE /budgets/{id}` |
| Invite | `POST /members` |
| Account dialog Save | `PATCH /members/{id}` |
| Remove member | `DELETE /members/{id}` |
| Open Profile | none (uses the session) |
| Profile fields, language, theme | `PATCH /me` |

---

## 11. Language and theme

### 11.1 Translation keys

- Languages: English (`en`) and Spanish (`es`).
- Every visible string is looked up by a translation key, e.g. `budget_amount` → "Budget amount" / "Monto del presupuesto". That includes activity sentences, error messages, empty states and date templates.
- Keys are snake_case and named after what they label, not where they appear.
- Placeholders use `{name}` and are filled at lookup time. Lookup never produces markup.
- Strings that depend on a count have a key per plural category, e.g. `transactions_count_one` and `transactions_count_other`. The category comes from `Intl.PluralRules` in the user's language.
- User data is never translated: budget names, payees, member names, the household name, the currency sign.
- Numbers are not localized (§ 9.1).

### 11.2 Which language is shown

1. The user's saved preference, if any.
2. Otherwise the browser's: `es` when `navigator.language` starts with `es`, `en` for everything else.

Before sign-in only rule 2 applies. New members start with no preference, so they see their browser's language until they pick one in Profile. Profile highlights the language currently in effect.

### 11.3 Adding a language

One new locale file with every key, plus the new code in the `language` enum (API_SURFACE.md § 12). Nothing else changes.

### 11.4 Theme

- Themes: Light, Dark, System. Per-user preference. System follows `prefers-color-scheme`.
- Light theme tokens are the reference design's, in `frontend/src/styles/index.css`.
- Dark theme tokens are derived from the light ones. **Pending review by the project owner.**
- Fonts: DM Sans for text, DM Mono for every figure. Self-hosted, not loaded from Google Fonts.
