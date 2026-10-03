/**
 * Record endpoints — API_SURFACE.md § 4.
 *
 * Transactions and budgets share one port; the `type` parameter picks the table.
 */
import { request } from "./client";
import type {
  MoneyRecord,
  PageSize,
  RecordCreateInput,
  RecordType,
  RecordUpdateInput,
} from "@/types/api";

export interface RecordQuery {
  type: RecordType;
  /** Required for transactions; ignored by the backend for budgets. */
  month?: string;
  page?: number;
  q?: PageSize;
  search?: string;
}

/** List one page of records, plus the pagination meta. */
export function fetchRecords(query: RecordQuery) {
  return request<MoneyRecord[]>("/api/v1/records", {
    query: {
      type: query.type,
      month: query.month,
      page: query.page ?? 1,
      q: query.q ?? 10,
      search: query.search,
    },
  });
}

/** Create a transaction or a budget. Flow and user come from the backend. */
export function createRecord(input: RecordCreateInput) {
  return request<MoneyRecord>("/api/v1/records", { method: "POST", body: input });
}

/** Partially update a record. `type` routes the id to the right table. */
export function updateRecord(
  id: number,
  type: RecordType,
  patch: RecordUpdateInput,
) {
  return request<MoneyRecord>(`/api/v1/records/${id}`, {
    method: "PATCH",
    body: patch,
    query: { type },
  });
}

/** Soft-delete one record. */
export function deleteRecord(id: number, type: RecordType) {
  return request<null>(`/api/v1/records/${id}`, {
    method: "DELETE",
    query: { type },
  });
}

/** Bulk soft-delete for the multi-select, all-or-nothing, at most 100 ids. */
export function deleteRecords(ids: number[], type: RecordType) {
  return request<{ deleted: number }>("/api/v1/records", {
    method: "DELETE",
    query: { type, ids: ids.join(",") },
  });
}
