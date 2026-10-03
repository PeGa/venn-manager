/**
 * Money formatting and amount parsing (FRONTEND.md § 9.1, § 9.3).
 *
 * Amounts are integer cents end to end. Numbers are never locale-formatted:
 * `,` groups thousands and `.` separates decimals in every language.
 */

/** Largest magnitude the API accepts (API_SURFACE.md § 0). */
export const CENTS_LIMIT = 9_999_999_999;

const MINUS = "−";
const AMOUNT = /^([+\-−]?)(\d+)(?:[.,](\d{1,2}))?$/;

export interface MoneyFormat {
  /** 2 for transactions, forecast and balance; 0 for totals and budgets. */
  decimals?: 0 | 2;
  /** Prefix positive amounts with `+` (income in lists, forecast terms). */
  signed?: boolean;
}

function group(units: bigint): string {
  return units.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

/** `sign + currencySign + digits`, e.g. `−$1,629` or `+$2,240.00`. */
export function formatMoney(
  cents: number,
  currencySign: string,
  { decimals = 2, signed = false }: MoneyFormat = {},
): string {
  const magnitude = BigInt(Math.abs(cents));
  let digits: string;
  if (decimals === 0) {
    digits = group((magnitude + 50n) / 100n);
  } else {
    const fraction = (magnitude % 100n).toString().padStart(2, "0");
    digits = `${group(magnitude / 100n)}.${fraction}`;
  }
  const isZero = digits.replace(/[0.,]/g, "") === "";
  const sign = isZero ? "" : cents < 0 ? MINUS : signed ? "+" : "";
  return `${sign}${currencySign}${digits}`;
}

/**
 * Parse what a person typed into integer cents, or `null` when it is not an
 * amount. Accepts an optional sign, `.` or `,` as decimal separator with at
 * most two decimals, and ignores spaces. Thousands separators are rejected.
 */
export function parseAmount(text: string): number | null {
  const match = AMOUNT.exec(text.replace(/\s+/g, ""));
  if (match === null) {
    return null;
  }
  const [, sign = "", units = "", fraction = ""] = match;
  const cents = Number(units) * 100 + Number(fraction.padEnd(2, "0"));
  if (cents > CENTS_LIMIT) {
    return null;
  }
  const negative = cents !== 0 && (sign === "-" || sign === MINUS);
  return negative ? -cents : cents;
}
