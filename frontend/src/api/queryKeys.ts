/**
 * Query keys and cache policy.
 *
 * Centralised so an invalidation cannot miss a key: every hook builds its key
 * through these helpers, and every mutation invalidates through them too.
 */
import type { RecordType } from "@/types/api";

export const keys = {
  session: ["session"] as const,
  settings: ["settings"] as const,
  users: ["users"] as const,
  concepts: ["concepts"] as const,
  monthState: ["current-month"] as const,
  projections: (month: string) => ["projections", month] as const,
  records: (params: {
    type: RecordType;
    month?: string;
    page: number;
    size: number | "all";
    search: string;
  }) => ["records", params] as const,
};

/**
 * `staleTime` for read queries.
 *
 * AGENTS.md § Performance Guardrails: the frontend must not refetch on every
 * render. Thirty seconds is short enough that a peer's change appears on the
 * next navigation and long enough that re-rendering a screen is free.
 */
export const STALE_TIME_MS = 30_000;

/**
 * How often the month state is polled.
 *
 * FRONTEND.md § 2 and BACKEND.md § 3.5: the frontend polls for a month change.
 * There is no WebSocket or SSE (AGENTS.md § What NOT to Do).
 */
export const MONTH_POLL_MS = 60_000;

/**
 * Retry policy: network failures only, at most three attempts in total.
 *
 * A contract error (422, 409, 410…) is a definite answer and retrying it would
 * only repeat the same rejection, so those fail fast.
 */
export const MAX_ATTEMPTS = 3;
