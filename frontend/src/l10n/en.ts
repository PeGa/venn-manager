/**
 * English strings. This object defines the translation-key set: every other
 * locale is typed against it, so a missing or extra key fails the build.
 *
 * Keys are snake_case and named after what they label. Plural-dependent
 * strings come as `<base>_<category>` with at least `<base>_other`.
 */
export const en = {
  app_name: "Venn Manager",
  nav_overview: "Overview",
  nav_budget: "Budget",
  nav_transactions: "Transactions",
  nav_history: "History",
  nav_goals: "Goals",
  nav_balance: "Balance",
  nav_settings: "Settings",

  day_today: "Today",
  day_yesterday: "Yesterday",
  day_month: "{month} {day}",
  just_now: "Just now",
  period_label: "{month} {start}–{end}",
  month_title: "{month} {year}",

  schedule_none: "No due date",
  schedule_once: "Once · {date}",
  schedule_weekly: "Weekly · {weekday}s",
  schedule_biweekly: "Every 2 weeks · from {date}",
  schedule_monthly: "Monthly · {day}",
  ordinal_one: "{n}st",
  ordinal_two: "{n}nd",
  ordinal_few: "{n}rd",
  ordinal_other: "{n}th",

  due_overdue: "Overdue",
  due_today: "Due today",
  due_tomorrow: "Due tomorrow",
  due_in_days_one: "Due in {n} day",
  due_in_days_other: "Due in {n} days",

  transactions_count_one: "{n} transaction",
  transactions_count_other: "{n} transactions",

  note_spent_left: "{actual} spent · {left} left",
  note_spent_over: "{actual} spent · {over} over",
  note_received_to_go: "{actual} received · {left} to go",
  note_received_above: "{actual} received · {over} above",
  note_zero_empty: "{actual} · Set an amount",
  note_zero_spent: "{actual} spent · Set an amount",
  note_zero_received: "{actual} received · Set an amount",
  note_goal_progress: "{actual} of {amount} · {left} to go",
  note_goal_reached: "Reached",
  note_goal_over: "{over} over",

  act_tx_create: "added “{payee}”",
  act_tx_update: "edited “{payee}”",
  act_tx_delete: "removed “{payee}”",
  act_tx_bulk_delete_one: "removed {n} transaction",
  act_tx_bulk_delete_other: "removed {n} transactions",
  act_budget_create: "added the {name} budget",
  act_budget_rename: "renamed {oldName} to {name}",
  act_budget_amount: "set the {name} budget to {amount}",
  act_budget_schedule: "changed when {name} is due",
  act_budget_goal_on: "made {name} a goal",
  act_budget_goal_off: "moved {name} back to Budget",
  act_budget_delete: "removed the {name} budget",
  act_member_invite: "added {name} to the household",
  act_member_update: "updated {name}'s account",
  act_member_remove: "removed {name} from the household",
  act_settings_currency: "changed the currency sign to {sign}",
  act_settings_currency_cleared: "removed the currency sign",
  act_settings_name: "renamed the household to {name}",
  act_settings_timezone: "changed the timezone to {timezone}",
  act_settings_opening_balance: "set the opening balance to {amount}",
  act_settings_member_income_on: "turned member income on",
  act_settings_member_income_off: "turned member income off",
};
