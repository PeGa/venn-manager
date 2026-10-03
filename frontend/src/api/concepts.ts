/**
 * Concept endpoints — API_SURFACE.md § 3.3.
 */
import { request } from "./client";
import type { Concept, Flow } from "@/types/api";

/**
 * List concepts.
 *
 * The list is never paginated, so the Concepts grid filters and pages it
 * client-side. Pickers use the default list, which excludes deleted concepts.
 */
export function fetchConcepts(options: { flow?: Flow; includeDeleted?: boolean } = {}) {
  return request<Concept[]>("/api/v1/settings/concepts", {
    query: { flow: options.flow, include_deleted: options.includeDeleted ?? false },
  });
}

/** Create a concept. `flow` is fixed for the concept's whole life. */
export function createConcept(name: string, flow: Flow) {
  return request<Concept>("/api/v1/settings/concepts", {
    method: "POST",
    body: { name, flow },
  });
}

/** Rename a concept. The new name applies to every record that references it. */
export function renameConcept(id: number, name: string) {
  return request<Concept>(`/api/v1/settings/concepts/${id}`, {
    method: "PATCH",
    body: { name },
  });
}

/** Soft-delete one concept. Its budgets and working-month records disappear. */
export function deleteConcept(id: number) {
  return request<null>(`/api/v1/settings/concepts/${id}`, { method: "DELETE" });
}

/** Bulk soft-delete, all-or-nothing, at most 100 ids per request. */
export function deleteConcepts(ids: number[]) {
  return request<{ deleted: number }>("/api/v1/settings/concepts", {
    method: "DELETE",
    query: { ids: ids.join(",") },
  });
}
