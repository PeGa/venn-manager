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
};
