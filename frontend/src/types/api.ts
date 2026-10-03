/**
 * Wire types for CONTRACTS/API_SURFACE.md.
 *
 * These mirror the API exactly, including its snake_case field names: the
 * contract is the source of truth, and renaming fields here would only create a
 * second place to keep in sync.
 */

/** Direction of a money movement. A concept is permanently one or the other. */
export type Flow = "in" | "out";

/** Colour theme. `system` follows the OS preference. */
export type Theme = "light" | "dark" | "system";

/** Shipped locales (API_SURFACE.md § 3.1). */
export type Language = "en" | "es";

/** The two record kinds the unified `/records` port serves. */
export type RecordType = "transaction" | "budget";

/** Page sizes the contract allows, plus the explicit "everything" option. */
export type PageSize = 10 | 20 | 50 | "all";

/** Error codes from API_SURFACE.md § Error Codes. */
export type ErrorCode =
  | "UNAUTHORIZED"
  | "FORBIDDEN"
  | "PASSWORD_CHANGE_REQUIRED"
  | "NOT_FOUND"
  | "CONFLICT"
  | "GONE"
  | "VALIDATION_ERROR"
  | "INTERNAL_ERROR";

/** A user as exposed by the API. Password hashes are never returned. */
export interface UserSummary {
  id: number;
  username: string;
  real_name: string;
  is_admin: boolean;
}

/** `POST /auth/login` and `GET /auth/session` payloads. */
export interface SessionPayload {
  user: UserSummary;
  /**
   * Derived at login, never stored. While true the session may only call
   * `POST /auth/password`.
   */
  must_change_password: boolean;
}

/** `GET /settings`: global settings merged with the caller's own. */
export interface Settings {
  currency: string;
  language: Language;
  theme: Theme;
  last_acknowledged_month: string;
  username: string;
  real_name: string;
}

/** One concept from `GET /settings/concepts`. */
export interface Concept {
  id: number;
  name: string;
  flow: Flow;
  created_by: string | null;
  /** Lets the UI render the faint "(deleted)" tag on the creator. */
  created_by_is_deleted: boolean;
  created_at: string;
  is_deleted: boolean;
}

/** The unified record shape (API_SURFACE.md § 4). */
export interface MoneyRecord {
  id: number;
  type: RecordType;
  date: string;
  concept_id: number;
  concept_name: string;
  concept_flow: Flow;
  /** True when the concept was soft-deleted; only possible in History. */
  concept_is_deleted: boolean;
  /** Always a number for a transaction; nullable for a budget. */
  amount: number | null;
  user_id: number;
  username: string;
  user_is_deleted: boolean;
  created_at: string;
}

/** `GET /projections`. All figures are two-decimal numbers. */
export interface Projections {
  spend_projection: number;
  earn_projection: number;
  savings_projection: number;
  actual_spend: number;
  actual_earn: number;
  /**
   * The unspent part of `spend_projection`: `spend_projection` always equals
   * `actual_spend + spend_budget_remaining`, which is what the widget sub-line
   * spells out.
   */
  spend_budget_remaining: number;
  /** The income still expected to land. No identity with `earn_projection`. */
  earn_budget_remaining: number;
}

/** `GET /current-month`. */
export interface MonthState {
  current_month: string;
  /** The user's working month: what Home and Budget operate on. */
  last_acknowledged_month: string;
  needs_switch: boolean;
  /** Month of the oldest live transaction, or null when there are none. */
  earliest_month: string | null;
}

/** Pagination block. Present only when `q` is numeric. */
export interface PageMeta {
  page: number;
  per_page: number;
  total: number;
  total_pages: number;
}

/** Every response, success or failure, uses this envelope. */
export interface Envelope<T> {
  data: T | null;
  error: { code: ErrorCode; message: string } | null;
  meta: PageMeta | null;
}

/** Body accepted by `POST /records`. */
export interface RecordCreateInput {
  type: RecordType;
  date: string;
  concept_id: number;
  amount?: number | string | null;
}

/** Body accepted by `PATCH /records/:id`. Every field is optional. */
export interface RecordUpdateInput {
  date?: string;
  concept_id?: number;
  amount?: number | string | null;
}
