/** Spanish strings, typed against the English key set. */
import type { TranslationTable } from "@/l10n";

export const es: TranslationTable = {
  app_name: "Venn Manager",
  nav_overview: "Resumen",
  nav_budget: "Presupuesto",
  nav_transactions: "Movimientos",
  nav_history: "Historial",
  nav_goals: "Metas",
  nav_balance: "Saldo",
  nav_settings: "Ajustes",

  day_today: "Hoy",
  day_yesterday: "Ayer",
  day_month: "{day} {month}",
  just_now: "Ahora mismo",
  period_label: "{start}–{end} {month}",
  month_title: "{month} {year}",

  schedule_none: "Sin vencimiento",
  schedule_once: "Una vez · {date}",
  schedule_weekly: "Semanal · {weekday}",
  schedule_biweekly: "Cada 2 semanas · desde {date}",
  schedule_monthly: "Mensual · día {day}",
  ordinal_one: "{n}",
  ordinal_two: "{n}",
  ordinal_few: "{n}",
  ordinal_other: "{n}",

  due_overdue: "Vencido",
  due_today: "Vence hoy",
  due_tomorrow: "Vence mañana",
  due_in_days_one: "Vence en {n} día",
  due_in_days_other: "Vence en {n} días",

  transactions_count_one: "{n} transacción",
  transactions_count_other: "{n} transacciones",
};
