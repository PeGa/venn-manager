/**
 * Display formatting.
 *
 * Deliberately locale-free: AGENTS.md forbids locale-aware number formatting,
 * and FRONTEND.md only ever asks for two decimals. Dates stay in the API's
 * `YYYY-MM-DD` form for the same reason, so there is no date formatter here.
 */

/** Render a number with exactly two decimals and no grouping separator. */
export function formatAmount(value: number): string {
  return value.toFixed(2);
}

/**
 * Render an amount that may legitimately be absent.
 *
 * A budget without a reserved amount is empty, not zero (FRONTEND.md § 2), so
 * `null` must not collapse to "0.00".
 */
export function formatNullableAmount(value: number | null): string {
  return value === null ? "" : formatAmount(value);
}

/** Prefix the currency symbol. The symbol is display-only and never computed. */
export function formatMoney(value: number, currency: string): string {
  return `${currency}${formatAmount(value)}`;
}
