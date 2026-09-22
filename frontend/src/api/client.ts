/** Typed API client for the Venn Manager backend.
 *
 * All functions return parsed JSON. Errors throw ApiError objects.
 * Credentials are sent with every request for session cookie auth.
 */

import type {
  ApiError,
  BudgetEntry,
  Concept,
  MonthStatus,
  Projections,
  Settings,
  Transaction,
  User,
} from "../types/index.ts";

const BASE = "/api";

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${url}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  if (!res.ok) {
    const body: ApiError = await res.json().catch(() => ({
      error: "UNKNOWN",
      detail: "An unexpected error occurred",
    }));
    throw body;
  }

  return res.json() as Promise<T>;
}

// Auth
export const login = (username: string, password: string) =>
  request<{ user: User }>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });

export const logout = () =>
  request<{ ok: boolean }>("/auth/logout", { method: "POST" });

export const getMe = () => request<{ user: User }>("/auth/me");

export const changePassword = (current_password: string, new_password: string) =>
  request<{ ok: boolean }>("/auth/change-password", {
    method: "POST",
    body: JSON.stringify({ current_password, new_password }),
  });

// Records
export const getRecords = (month: string, filter?: string) => {
  const params = new URLSearchParams({ month });
  if (filter) params.set("filter", filter);
  return request<{ records: Transaction[] }>(`/records?${params}`);
};

export const createRecord = (date: string, concept_id: number, amount: number) =>
  request<Transaction>("/records", {
    method: "POST",
    body: JSON.stringify({ date, concept_id, amount }),
  });

export const updateRecord = (id: number, data: { date?: string; concept_id?: number; amount?: number }) =>
  request<Transaction>(`/records/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });

export const deleteRecord = (id: number) =>
  request<{ deleted: boolean }>(`/records/${id}`, { method: "DELETE" });

export const bulkDeleteRecords = (ids: number[]) =>
  request<{ deleted_count: number }>("/records/bulk", {
    method: "DELETE",
    body: JSON.stringify({ ids }),
  });

// Concepts
export const getConcepts = (filter?: string) => {
  const params = new URLSearchParams();
  if (filter) params.set("filter", filter);
  const qs = params.toString();
  return request<{ concepts: Concept[] }>(`/concepts${qs ? `?${qs}` : ""}`);
};

export const createConcept = (name: string, flow: "IN" | "OUT") =>
  request<Concept>("/concepts", {
    method: "POST",
    body: JSON.stringify({ name, flow }),
  });

export const updateConcept = (id: number, name: string) =>
  request<Concept>(`/concepts/${id}`, {
    method: "PUT",
    body: JSON.stringify({ name }),
  });

export const deleteConcept = (id: number) =>
  request<{ deleted: boolean }>(`/concepts/${id}`, { method: "DELETE" });

export const bulkDeleteConcepts = (ids: number[]) =>
  request<{ deleted_count: number }>("/concepts/bulk", {
    method: "DELETE",
    body: JSON.stringify({ ids }),
  });

// Budget
export const getBudget = (month: string, filter?: string) => {
  const params = new URLSearchParams({ month });
  if (filter) params.set("filter", filter);
  return request<{ budget: BudgetEntry[] }>(`/budget?${params}`);
};

export const createBudget = (date: string, concept_id: number, amount: number | null) =>
  request<BudgetEntry>("/budget", {
    method: "POST",
    body: JSON.stringify({ date, concept_id, amount }),
  });

export const updateBudget = (id: number, data: { date?: string; concept_id?: number; amount?: number | null }) =>
  request<BudgetEntry>(`/budget/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });

export const deleteBudget = (id: number) =>
  request<{ deleted: boolean }>(`/budget/${id}`, { method: "DELETE" });

export const bulkDeleteBudget = (ids: number[]) =>
  request<{ deleted_count: number }>("/budget/bulk", {
    method: "DELETE",
    body: JSON.stringify({ ids }),
  });

// History
export const getHistory = (month: string, filter?: string) => {
  const params = new URLSearchParams({ month });
  if (filter) params.set("filter", filter);
  return request<{ records: Transaction[] }>(`/history?${params}`);
};

export const getHistoryMonths = () =>
  request<{ months: string[] }>("/history/months");

// Projections
export const getProjections = (month: string) =>
  request<Projections>(`/projections?month=${month}`);

// Month
export const getMonthStatus = () =>
  request<MonthStatus>("/month/status");

export const switchMonth = () =>
  request<{ switched: boolean; new_month: string }>("/month/switch", { method: "POST" });

// Settings
export const getSettings = () => request<Settings>("/settings");

export const setCurrency = (currency: string) =>
  request<{ currency: string }>("/settings/currency", {
    method: "PUT",
    body: JSON.stringify({ currency }),
  });

export const setLanguage = (language: string) =>
  request<{ language: string }>("/settings/language", {
    method: "PUT",
    body: JSON.stringify({ language }),
  });

export const setTheme = (theme: string) =>
  request<{ theme: string }>("/settings/theme", {
    method: "PUT",
    body: JSON.stringify({ theme }),
  });

// Users (admin)
export const getUsers = () => request<{ users: User[] }>("/users");

export const createUser = (username: string, real_name: string, password: string, is_admin: boolean) =>
  request<User>("/users", {
    method: "POST",
    body: JSON.stringify({ username, real_name, password, is_admin }),
  });

export const updateUser = (id: number, data: { username?: string; real_name?: string; password?: string; is_admin?: boolean }) =>
  request<User>(`/users/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });

export const deleteUser = (id: number) =>
  request<{ deleted: boolean }>(`/users/${id}`, { method: "DELETE" });
