/** Formatting utilities for amounts and dates. */

/** Format a number as a currency amount with exactly 2 decimal places. */
export const formatAmount = (value: number): string => {
  return value.toFixed(2);
};

/** Format a YYYY-MM-DD date string for display. */
export const formatDate = (dateStr: string): string => {
  return dateStr;
};

/** Get current month as YYYY-MM string. */
export const getCurrentMonth = (): string => {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  return `${year}-${month}`;
};

/** Get today's date as YYYY-MM-DD string. */
export const getToday = (): string => {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
};
