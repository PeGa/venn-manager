/** Shared TypeScript type definitions matching backend contract shapes. */

export interface User {
  readonly id: number;
  readonly username: string;
  readonly real_name: string;
  readonly is_admin: boolean;
  readonly language: string;
  readonly theme: string;
  readonly created_at: string;
  readonly must_change_password?: boolean;
}

export interface Concept {
  readonly id: number;
  readonly name: string;
  readonly flow: "IN" | "OUT";
  readonly created_by: number;
  readonly username: string;
  readonly created_at: string;
}

export interface Transaction {
  readonly id: number;
  readonly date: string;
  readonly concept_id: number;
  readonly concept_name: string;
  readonly flow: "IN" | "OUT";
  readonly amount: number;
  readonly user_id: number;
  readonly username: string;
  readonly created_at: string;
}

export interface BudgetEntry {
  readonly id: number;
  readonly date: string;
  readonly concept_id: number;
  readonly concept_name: string;
  readonly flow: "IN" | "OUT";
  readonly amount: number | null;
  readonly user_id: number;
  readonly username: string;
  readonly created_at: string;
}

export interface Projections {
  readonly current_out: number;
  readonly current_in: number;
  readonly savings_projection: number;
  readonly spend_projection: number;
  readonly earn_projection: number;
}

export interface Settings {
  readonly currency: string;
  readonly language: string;
  readonly theme: string;
}

export interface MonthStatus {
  readonly current_month: string;
  readonly active_month: string;
  readonly switch_available: boolean;
}

export interface ApiError {
  readonly error: string;
  readonly detail: string;
}
