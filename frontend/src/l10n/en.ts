/**
 * English strings.
 *
 * This object defines the translation-key set: `es.ts` must satisfy
 * `Record<TranslationKey, string>`, so a missing or extra key is a compile
 * error rather than a runtime gap.
 *
 * Keys are snake_case and named after what they label, not where they appear,
 * so a string can move between screens without a rename.
 */
export const en = {
  // Shared vocabulary
  app_name: "Venn Manager",
  save: "Save",
  cancel: "Cancel",
  close: "Close",
  delete: "Delete",
  edit: "Edit",
  add: "Add",
  confirm: "Confirm",
  loading: "Loading…",
  retry: "Retry",
  search: "Search",
  search_placeholder: "Filter by concept…",
  no_results: "Nothing to show yet.",
  deleted_tag: "(deleted)",
  required_note: "Required",
  flow_in: "In",
  flow_out: "Out",
  date_column: "Date",
  concept_column: "Concept",
  amount_column: "Amount",
  flow_column: "Flow",
  user_column: "User",
  rows_per_page: "Rows",
  page_label: "Page {page} of {total}",
  pagination_all: "All",
  pagination_previous: "Previous page",
  pagination_next: "Next page",
  select_row: "Select row {name}",

  // Navigation
  menu_open: "Open navigation",
  menu_close: "Close navigation",
  nav_home: "Home",
  nav_budget: "Budget",
  nav_concepts: "Concepts",
  nav_history: "History",
  nav_configuration: "Configuration",

  // Record actions (Home, Budget, History)
  add_record: "Add record",
  edit_record: "Edit record",
  delete_record: "Delete record",
  delete_records_count: "Delete {count} selected",
  selection_hint: "Tap rows to select them, then confirm the deletion.",
  selected_count: "{count} selected",
  clear_selection: "Clear selection",

  // Home widgets (FRONTEND.md § 1.2)
  home_title: "Home",
  widget_actual_out: "Spent so far",
  widget_actual_in: "Earned so far",
  widget_savings_projection: "Savings projection",
  widget_spend_projection: "Spend projection",
  widget_earn_projection: "Earn projection",
  widget_spend_breakdown: "{spent} spent + {remaining} of budget left",
  widget_earn_breakdown: "{booked} booked + {remaining} still expected",
  widget_earn_none: "no income booked yet",

  // Budget
  budget_title: "Budget",
  budget_amount_optional: "Amount (optional)",
  budget_hint:
    "Budget entries persist across months. Their date is the planned day of the movement, shown inside the working month.",

  // Month switch (FRONTEND.md § 2, BACKEND.md § 3)
  switch_cta: "Switch to current month",
  month_switch_title: "A new month started",
  month_switch_body:
    "The calendar moved to {current}. Your records and budgets stay untouched — the new month simply starts with no transactions yet. Switch now?",
  month_switch_confirm: "Switch to {current}",
  month_switch_decline: "Stay on {working}",

  // Concepts
  concepts_title: "Concepts",
  add_concept: "Add concept",
  edit_concept: "Edit concept",
  show_deleted: "Show deleted",
  concept_name_label: "Concept",
  concept_flow_label: "Flow",
  concept_created_column: "Date",
  rename_warning_title: "Rename this concept?",
  rename_warning_body:
    "Records reference concepts by id, so the new name appears everywhere — including previous months.",
  delete_concept_warning_title: "Delete this concept?",
  delete_concept_warning_body:
    "Its budget entries and this month's records will disappear. Previous months keep them, marked as deleted. There is no undo.",
  flow_immutable_note: "Flow cannot be changed. Delete the concept and create a new one instead.",

  // History
  history_title: "History",
  history_month_label: "Month",
  history_readonly_note: "History is read only.",
  no_previous_months: "No previous months to show",

  // Configuration
  configuration_title: "Configuration",
  profile_title: "Profile",
  management_title: "Management",
  logout: "Log out",
  username_label: "Username",
  real_name_label: "Real name",
  current_password_label: "Current password",
  password_label: "Password",
  new_password_label: "New password",
  repeat_password_label: "Repeat password",
  language_label: "Application language",
  currency_label: "Currency",
  theme_label: "Colour theme",
  theme_light: "Light",
  theme_dark: "Dark",
  theme_system: "System",
  change_password: "Change password",
  currency_warning_title: "Currency affects everyone",
  currency_warning_body:
    "Currency is a global setting. Changing it updates the app for every user. Continue?",
  users_grid_title: "Users",
  add_user: "Add user",
  is_admin_column: "Is administrator",
  delete_user_warning_title: "Delete this user?",
  delete_user_warning_body:
    "They will no longer be able to sign in and their name is marked as deleted. Their records stay, and the username cannot be reused. There is no undo.",

  // Auth
  login_title: "Sign in",
  sign_in: "Sign in",
  force_change_title: "Choose a new password",
  force_change_body:
    "You are signed in with the default password. Set your own to continue.",

  // Errors
  error_unauthorized: "Your session ended. Please sign in again.",
  error_forbidden: "You are not allowed to do that.",
  error_password_change_required: "Change your password to continue.",
  error_not_found: "That record does not exist.",
  error_conflict: "That value is already in use.",
  error_gone: "Record not available anymore.",
  error_validation: "Check the highlighted fields.",
  error_internal: "Something went wrong on the server.",
  error_network: "Cannot reach the server.",
  error_unknown: "Something went wrong.",

  // Validation
  validation_required: "This field is required.",
  validation_amount: "Enter an amount with at most two decimals.",
  validation_date: "Enter a valid date.",
  validation_concept_name: "Enter a name of 64 characters or fewer.",
  validation_currency: "Currency must be a single character.",
  validation_password_short: "Use at least 8 characters.",
  validation_password_mismatch: "The passwords do not match.",
  validation_username: "Enter a username of 64 characters or fewer.",
  validation_real_name: "Enter a name of 128 characters or fewer.",
} as const;

/** Every key a locale must provide. */
export type TranslationKey = keyof typeof en;
