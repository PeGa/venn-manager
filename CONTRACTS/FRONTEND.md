# Venn Manager
## General description

Venn Manager (aka venn-manager, from now on called 'the app') is a multi-language web app (python+sqlalchemy+flask backend / preact+vite+tailwind frontend with typescript flavor) that helps managing a shared wallet across one or more users: a couple, roommates, any number of people on the same household. This last part is important: This is not a debt-tracker, nor anything to store who owes who in any form: This is a shared (single) ledger for people collaborating towards the same financial goal, giving the ability to forecast monthly spending and earning, as means for financial organization. Nothing else.

Multi-language is done achieving client-side l10n via translation keys + locale files (example: `__date_column` can be translated to both `Fecha` or `Date`), and later set on a per-user basis. Locale doesn't account for currency sign given it's arbitrary.

The app allows standard auth (session with cookies, no JWT) with a user admin that allows for user granting + any added users by the admin. The app by itself doesn't allow for registration, so standard deployments should allow for a first login with a predefined admin /password login, seeded in the database on the first run (i.e. first migration) and forcing a password change right after logging in. Any users added have the exact same permissions as the administrator user, except user creation. Any record created in the database is linked to users, so any user will know who and when added what record, at any moment. This doesn't mean audit trail, just visual identification. Removing records is trivial and implies a logical deletion (soft delete, for database consistency; there is no trash, restore or undo: a removed record is gone from the UI), gated by a confirmation dialog. Any user can remove any record, because the target of this application is expected to work on agreement among peers.

### Frontend behavior

#### 1. Main screen
Once users logged in, they're presented in a dashboard taht will contain the following elements:

1. A main workspace with a grid containing the following columns:

| Date | Concept |Amount|Flow | User |
|------| --------|------|-----|------|

    1. Concept is the accounting concept (or, more coloquially, the item name/description/note) of the item. Under the menu entry [Concepts] (see section 3. Concepts), it shows to the user as a collection of strings that will be used to represent different operations (both In and Out). However, Concepts will be tied to specific In or Out operations: `Income` is not an `Out` operation, the same way that `Groceries` isn't an `In` operation. Note: A concept without picking a `Flow` can't be recorded. In the Add Record modal, Flow is auto-populated based on the selected Concept and is not manually selectable.
    2. Flow has two possible values: In or Out (Income / Spending, respectively).
    3. User column will print the username that registered that record.

2. A series of widgets above the grid stating:
    1. Amount of money with "Out" flow so far in the current month
    2. Amount of money with "In" flow so far in the current month
    3. Month's projection of the savings on the current month (i.e. projection of the substraction of next points: #5 minus #4)
    4. Month's projection of the "Out" money (i.e. projection of how much money will be spent) [See section 2: Budget] called [Spend projection]
    5. Month's projection of the "In" money (i.e. projection of how much money will be earned) [See section 2: Budget] called [Earn projection]

----

3. At the top-left side, a sandwich button that toggles a **Left Sidebar (Drawer)**. This sidebar slides in from the left edge of the screen, overlaying the main content. It contains the following navigation items:
    1. Home
        1. Add record (modal)
        2. Edit record (inline)
        3. Delete record (confirmation dialog)
    2. Budget [see section 2. Budget]
    3. Concepts [See section 3. Concepts]
    4. History [ See section 4. History ]
    5. Configuration  [See section 5. Configuration]

Record menu entries edit the table presented in the page the user is standing. While standing in the Home, the "Add"/"Edit"/"Delete" entries only affect the records on the main table. Both `Edit` and `Delete` entries will ask to select the entry to be altered. In the case of `Delete`, it offers the possibility to multi-select rows by tapping on then.

Amount column will host numbers with two decimals. 0 becomes 0.00.

#### 2. Budget
Budget is a section composed entirely by a grid with the following structure:

| Date | Concept |Amount|Flow | User |
|------| --------|------|-----|------|

- [Date] presents a date picker when recording an entry.
- [Concept] has a `Concept` picker, that feeds from the recorded `Concepts` on `Concept` section [ See 3. Concepts ]
- [Amount] is a number that serves as placeholder for how much the user intends to spend or earn during the month. It can be empty, meaning the user doesn't have a reserved amount for that `Concept`. The same way, budgeted concepts account for what the user intend (in advance) to spend before actually spending them; thus, the importance of a `Date` field.
- [Flow] states In or Out, which means, Earn or Spend, respectively.
- [User] is which user added that record, that will be added automatically without the user's intervention.

The sum of `Out` records amounts for how much money the user plans to spend in the current month. That will be part of the `Spend projection` on the section 1.2.4. [ Spend Projection ] plus the current spending items (see below).

The sum of `In` records amounts for how much money the user plans to earn in the current month. That will be part of the `Earn projection` on the section 1.2.5. [ Earn Projection ] plus the actual earning items (see below).

The calculations aren't linear though: Both In and Out need to compute the respective actual records, in a way that:

Given budget records with the concepts A, B, C, D, n; and actual records named actualA, actualB, actualC, actualD, actualn:  the calculation should be (max(A, actualA) + max(B, actualB) + max(C, actualC) + max(D, actualD) + [max(n, actualn)]) + any other records outside the budget: If the budget contains elements A, B, C, D; the calculation is the above one + the records X, Y, Z that aren't found in the budget page.

In that way, the spending projection comprises both what's actually planned to be spent + what actually was spent and either wasn't budgeted or was overspent, in which case replaces any of its budgeted counterparts.

Same goes to the earning calculations but conversely: lowest instead of max, aiming for a pessimistic projection.

Budget records will remain as fixed amounts once the user sets them up, but the calculations (the projections) will reset every month. This is not a contradiction: Each month all spendings and income records (not budget, but actual spend/earning records) reset to 0, leaving only possible projected values what are already stored as Budget Concepts and their respective values. On the new month, user will be presented with a dialog to switch to the newly detected month, triggered by a specific API call that monitors current month [that's backend, not covered here]. Upon confirmation, the date field will switch the month to the following month, keeping the nearest possible day: 31 -> 30, 29 -> 28, and so on. This is a display rule only: the stored budget date is informational and never rewritten, so each budget date is shown inside the current (working) month, keeping its stored day clamped to that month's last day (a budget stored on the 31st shows as the 28th in February and as the 31st again in March). The Budget grid always lists every existing budget, regardless of the month its stored date belongs to. This date represents the target date for that specific money movement, not a creation date. Given this is a budget but not a transaction record, date serves as planning, not metadata for that specific record. If the user doesn't confirm, there will be a new CTA button on the top right of the grid, saying: "Switch to current month". Once done, previously current month is moved to `History` [See section 4. History].

----

At the top-left side, a sandwich button that toggles a **Left Sidebar (Drawer)**. This sidebar slides in from the left edge of the screen, overlaying the main content. It contains the following navigation items:
    1. Home [ See section 1: Main screen]
    2. Budget
        1. Add record (modal)
        2. Edit record (inline)
        3. Delete record (confirmation dialog)
    3. Concepts [See section 3. Concepts]
    4. History [ See section 4. History ]
    5. Configuration  [See section 5. Configuration]

Record menu entries edit the table presented in the page the user is standing. While standing in the `Budget` page, the "Add"/"Edit"/"Delete" entries only affect the records on the main table. Both `Edit` and `Delete` entries will ask to select the entry to be altered. In the case of `Delete`, it offers the possibility to multi-select rows by tapping on then.

#### 3. Concepts

The `Concepts` entry opens a new screen that features a grid with four colums:

| Date | Concept | Flow | User |

Date and user are automatically filled with current data. While `Date` is metadata, it's actually a visual identifier for any user that wants to track down when a specific Concept was created, to ensure validity in a given context.

Concept and Flow are the values the user has to pick. Flow is a drop-down menu of two items: In / Out. Concept, on the other hand, is a free string box. 64 chars max.

Deleting a concept is gated by a confirmation dialog warning that its budget entries and the current month's records for it will disappear as well (previous months keep them, see section 4). Renaming is gated by a confirmation dialog too, since the new name applies everywhere.

The grid offers a "Show deleted" toggle. When on, deleted concepts are listed with a fainter "(deleted)" tag and cannot be edited.

-----

At the top-left side, a sandwich button that toggles a **Left Sidebar (Drawer)**. This sidebar slides in from the left edge of the screen, overlaying the main content. It contains the following navigation items:
    1. Home [ See section 1: Main screen]
    2. Budget
    3. Concepts [See section 3. Concepts]
        1. Add record (modal)
        2. Edit record (inline)
        3. Delete record (confirmation dialog)
    4. History [ See section 4. History ]
    5. Configuration  [See section 5. Configuration]

Record menu entries edit the table presented in the page the user is standing. While standing in the `Concepts` page, the "Add"/"Edit"/"Delete" entries only affect the records on the main table. Both `Edit` and `Delete` entries will ask to select the entry to be altered. In the case of `Delete`, it offers the possibility to multi-select rows by tapping on then.

#### 4. History

History is exactly the same than Main screen, only that values locked to what a date picker at the top of the page dictates. Always resets to current month on first tap. Table is read only, not able to modify any item from the grid.

- Records whose concept was deleted remain visible in previous months, with the concept name followed by a fainter "(deleted)" tag (a state, not part of the name). The same applies to the User column when the user was deleted.
- The selectable months go from the oldest month with records up to the month before the current one.
- Current month on the date picker remains grayed out, so it's not selectable. The only way to show the current month in the History view, is by tapping the History View menu entry for the first time. 
    - If there is no previous month, date picker will stay grayed out, with a small legend that says: "No previous months to show". That will lead to: `History is exactly the same than Main screen, only that values locked to what a date picker at the top of the page dictates. Always resets to current month on first tap. It's read only, not able to modify any item from the table.` That is, History will show the current month status, read only, unable to pick any other month because there isn't any to show yet.

#### 5. Configuration

1. Configuration section allows for
    1. User creation [username], [Real Name], [Password] if the user is administrator + management of existing users.
        1. There will be roles and users. The user(s) with admin role will be the only permitted to manage (and create new) users.
        2. Every user will have the same permissions as the admin users, except for the user management, exclusive to the admin role.
        3. In the user management screen, users will be presented in a grid according the following fashion: | Username | Real name | Password | Repeat password | Is administrator |
            1. `Repeat password` will actually match the written passwords.
            2. The column "Is administrator" is a boolean.
    2. Modify administrator password / maintain user passwords
        1. Besides the grid shown in 3.1.1.3, there will be other routes to recover access.
        2. Email recovery isn't in the roadmap.
        3. However, a cli ocs-like (nextcloud cli) or artisan-like (laravel cli) could serve as a quick maintenance tool. It could both handle migrations and password recovery. Not planned yet.
    3. Set the currency for the app
        1. Multiple currencies support, conversion among currencies are not on the app's roadmap.
        2. Currency is just a character, not a picker. If the user wants to use a clown emoji as currency, the app won't get in the middle (ideally the symbol shown should be one grapheme cluster in length, despite of being a multi-codepoint character like an emoji. That said, an emoji for dollar sign is allowed, the 'USD' string is not.)
    4. Set the language
        1. Language support is described in the `General description` of this contract. Language modification is described in the Menu entries of the Configuration section [See section 5. Configuration]: Configuration -> Profile -> Application language.
    5. Set the color theme
        1. Light
        2. Dark
        3. System (i.e. Autodetect)

----

At the top-left side, a sandwich button that toggles a **Left Sidebar (Drawer)**. This sidebar slides in from the left edge of the screen, overlaying the main content. It contains the following navigation items:
    1. Home [see section 1. Home]
    2. Budget [see section 2. Budget]
    3. Concepts [See section 3. Concepts]
    4. History [ See section 4. History ]
    5. Configuration  [See section 5. Configuration]
        1. Profile. Will allow for:
            1. username change
            2. own password change
            3. real name change
            4. Application language
            5. Application currency. Note: currency is global and affects all users. Given the target for this application is people that has some degree of trust between individuals, currency is left as a value anybody can alter. Only gate for this operation is just a dialog informing the user that the confirming the action will affect all users.
        2. Management (only if logged user belongs to the Administrator role). Will allow for User management. User management belongs only to the administrator role.
        3. Log out


#### Appendix

These are some clarifications that generally apply to the whole app.

- This is a CONTRACT for FRONTEND. This contract DOES NOT UNDERSTAND BACKEND, only shows BEHAVIOR that should be provided and understood by an backend API.
- All grids are searchable (mostly for mobile usage)
- All grids are sorted by id (i.e. creation order) without possibility of changing sort order.
- All grids can be filtered (i.e. showing all records matching a specific substring) without compromising table boundaries: A filter on a given month won't carry results from a different month.
- Record grids (Home, Budget, History) are paginated with a selectable page size: 10, 20, 50 records at a time, or the full list.
- If a record was deleted by someone else while being edited or deleted, the action is cancelled, the grid refreshes, and the user sees "Record not available anymore."
- The "Current month" is each user's working month: it only advances when the user confirms the month switch.
- The same concept can't be in and out, given the concepts are tied to a specific flow. Intentional.
- l10n (not i18n) is very lax, affecting only the language. Numbering and other features are not planned yet.

##### Database assumptions

Being a frontend contract, this contract doesn't account for database settings, configurations or definitions. However, the following clarifications stand:

- Concept is an ID, so renaming a concept will affect the whole application. Renaming concepts should be gated with a confirmation though.
- On amounts and floating point precision: Assume `0.1+0.2 = 0.3`.
- On 5.1.1.3.2: The column "Is administrator" will directly tie to a is_admin column on the database. Boolean.
- Concurrency shouldn't be a problem. However, last write wins.
- Data export isn't planned yet.
- Undo / restore: not planned. Every deletion (records, budgets, concepts, users) is a soft delete, for consistency only.
- On Concept editing: Those Concept records (distinct from Transaction records, which are found in Home screen for example) can only alter the field `Concept`, not its `Flow`. Editing the flow is destructive; then, the best way to do so is to remove the flow record (the Concept itself) and create a new one with a different flow.
Flow deletion is a soft deletion to keep consistency with the old entries, so retaining the ID means old entries remain consistent. While this could lead to confusion, the grids have the column `Flow` for a reason.

