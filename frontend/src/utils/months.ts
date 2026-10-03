/**
 * Month arithmetic and the budget-date display rule.
 *
 * `YYYY-MM` sorts lexicographically, so comparisons are plain string compares.
 * The backend owns every stored date; nothing here writes anything back.
 */

const MONTH_LENGTH = 7;

/** Read the `YYYY-MM` part of an ISO date. */
export function monthOf(isoDate: string): string {
  return isoDate.slice(0, MONTH_LENGTH);
}

/** The month before *month*. */
export function previousMonth(month: string): string {
  const year = Number(month.slice(0, 4));
  const index = Number(month.slice(5, MONTH_LENGTH));
  return index === 1 ? `${year - 1}-12` : `${year}-${pad(index - 1)}`;
}

/** The month after *month*. */
export function nextMonth(month: string): string {
  const year = Number(month.slice(0, 4));
  const index = Number(month.slice(5, MONTH_LENGTH));
  return index === 12 ? `${year + 1}-01` : `${year}-${pad(index + 1)}`;
}

/** True when *left* is strictly earlier than *right*. */
export function isBeforeMonth(left: string, right: string): boolean {
  return left < right;
}

/** Number of days in a `YYYY-MM` month, leap years included. */
export function daysInMonth(month: string): number {
  const year = Number(month.slice(0, 4));
  const index = Number(month.slice(5, MONTH_LENGTH));
  // Day 0 of the next month is the last day of this one.
  return new Date(year, index, 0).getDate();
}

/**
 * Show a stored date inside *month*, keeping the day and clamping it.
 *
 * FRONTEND.md § 2 and BACKEND.md § 3.4: a budget stored on the 31st shows as the
 * 28th in February and as the 31st again in March. This is a display transform
 * only — the stored day is never rewritten, so no drift accumulates.
 */
export function clampDateToMonth(isoDate: string, month: string): string {
  const day = Number(isoDate.slice(8, 10));
  const clamped = Math.min(day, daysInMonth(month));
  return `${month}-${pad(clamped)}`;
}

/**
 * The months History may offer: *earliest* up to the month before the working
 * month.
 *
 * FRONTEND.md § 4: an empty result means the picker stays disabled and the
 * legend reads "No previous months to show".
 */
export function historyMonths(
  earliest: string | null,
  workingMonth: string,
): string[] {
  if (earliest === null || !isBeforeMonth(earliest, workingMonth)) {
    return [];
  }
  const months: string[] = [];
  for (
    let cursor = earliest;
    isBeforeMonth(cursor, workingMonth);
    cursor = nextMonth(cursor)
  ) {
    months.push(cursor);
  }
  return months;
}

function pad(value: number): string {
  return String(value).padStart(2, "0");
}
