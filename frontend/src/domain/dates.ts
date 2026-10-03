/**
 * Date labels (FRONTEND.md § 9.2). Names come from `Intl.DateTimeFormat`;
 * word order and wording come from the locale files.
 */
import type { IsoDate, IsoDateTime, MonthKey, Schedule } from "@/domain/model";
import { plural, translate, type Language } from "@/l10n";

const DAY_MS = 86_400_000;
const JUST_NOW_MS = 5 * 60_000;

function parts(day: IsoDate): [number, number, number] {
  const [year = 0, month = 1, date = 1] = day.split("-").map(Number);
  return [year, month, date];
}

function utc(day: IsoDate): number {
  const [year, month, date] = parts(day);
  return Date.UTC(year, month - 1, date);
}

function daysBetween(from: IsoDate, to: IsoDate): number {
  return Math.round((utc(to) - utc(from)) / DAY_MS);
}

function monthName(language: Language, month: number, style: "short" | "long"): string {
  const name = new Intl.DateTimeFormat(language, { month: style, timeZone: "UTC" }).format(
    Date.UTC(2000, month - 1, 1),
  );
  return name.replace(/\.$/, "");
}

/** "Sep 26" / "26 sept", without today or yesterday. */
export function dayMonth(language: Language, day: IsoDate): string {
  const [, month, date] = parts(day);
  return translate(language, "day_month", { month: monthName(language, month, "short"), day: date });
}

/** "Today", "Yesterday", otherwise "Sep 26". */
export function dayLabel(language: Language, day: IsoDate, today: IsoDate): string {
  const ago = daysBetween(day, today);
  if (ago === 0) {
    return translate(language, "day_today");
  }
  if (ago === 1) {
    return translate(language, "day_yesterday");
  }
  return dayMonth(language, day);
}

/** The calendar date of *instant* in *timezone*, as `YYYY-MM-DD`. */
export function localDate(instant: IsoDateTime, timezone: string): IsoDate {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: timezone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date(instant));
}

/** "Just now" for the last five minutes, otherwise the day label. */
export function activityTime(
  language: Language,
  at: IsoDateTime,
  now: Date,
  timezone: string,
  today: IsoDate,
): string {
  if (now.getTime() - Date.parse(at) < JUST_NOW_MS) {
    return translate(language, "just_now");
  }
  return dayLabel(language, localDate(at, timezone), today);
}

/** "SEP 1–30" / "1–30 SEPT", shown on every budget card. */
export function periodLabel(language: Language, start: IsoDate, end: IsoDate): string {
  const [, month, first] = parts(start);
  const [, , last] = parts(end);
  const name = monthName(language, month, "short").toUpperCase();
  return translate(language, "period_label", { month: name, start: first, end: last });
}

/** "September 2026" / "Septiembre 2026". */
export function monthTitle(language: Language, month: MonthKey): string {
  const [year, number] = parts(`${month}-01`);
  const name = monthName(language, number, "long");
  const capitalized = name.charAt(0).toUpperCase() + name.slice(1);
  return translate(language, "month_title", { month: capitalized, year });
}

function weekday(language: Language, day: IsoDate): string {
  return new Intl.DateTimeFormat(language, { weekday: "long", timeZone: "UTC" }).format(
    utc(day),
  );
}

/** The due chip: "Monthly · 1st", "Weekly · Mondays", "No due date"… */
export function scheduleSummary(language: Language, schedule: Schedule | null): string {
  if (schedule === null) {
    return translate(language, "schedule_none");
  }
  const { repeat, anchor } = schedule;
  switch (repeat) {
    case "once":
      return translate(language, "schedule_once", { date: dayMonth(language, anchor) });
    case "weekly":
      return translate(language, "schedule_weekly", { weekday: weekday(language, anchor) });
    case "biweekly":
      return translate(language, "schedule_biweekly", { date: dayMonth(language, anchor) });
    case "monthly": {
      const day = plural(language, "ordinal", parts(anchor)[2], {}, "ordinal");
      return translate(language, "schedule_monthly", { day });
    }
  }
}

/** The Coming up status line (FRONTEND.md § 5.1). */
export function dueStatus(
  language: Language,
  due: IsoDate,
  today: IsoDate,
  overdue: boolean,
): string {
  if (overdue) {
    return translate(language, "due_overdue");
  }
  const days = daysBetween(today, due);
  if (days === 0) {
    return translate(language, "due_today");
  }
  if (days === 1) {
    return translate(language, "due_tomorrow");
  }
  return plural(language, "due_in_days", days);
}
