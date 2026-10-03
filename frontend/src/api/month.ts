/**
 * Projection and month endpoints — API_SURFACE.md § 5 and § 2.
 */
import { request } from "./client";
import type { MonthState, Projections } from "@/types/api";

/** The five projection figures for one month. Computed per request. */
export function fetchProjections(month: string) {
  return request<Projections>("/api/v1/projections", { query: { month } });
}

/** Server month, the caller's working month, and whether a switch is pending. */
export function fetchMonthState() {
  return request<MonthState>("/api/v1/current-month");
}

/**
 * Acknowledge the month change.
 *
 * A state signal only: no record is archived and no budget is rewritten
 * (BACKEND.md § 3.2). Returns 409 when already on the current month.
 */
export function switchMonth() {
  return request<MonthState>("/api/v1/current-month/switch", { method: "POST" });
}
