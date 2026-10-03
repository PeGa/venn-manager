/**
 * Core value types shared by the domain and the API port (API_SURFACE.md § 0).
 */

/** Integer cents, signed. `-8412` is −84.12. */
export type Cents = number;
/** `YYYY-MM-DD`, household-local. */
export type IsoDate = string;
/** ISO 8601 instant with offset. */
export type IsoDateTime = string;
/** `YYYY-MM`. */
export type MonthKey = string;
export type Uuid = string;

export type Repeat = "once" | "weekly" | "biweekly" | "monthly";

/** When a budget is due (API_SURFACE.md § 1.4). */
export interface Schedule {
  repeat: Repeat;
  anchor: IsoDate;
}
