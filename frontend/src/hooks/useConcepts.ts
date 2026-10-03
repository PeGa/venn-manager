/**
 * Concept hooks (API_SURFACE.md § 3.3).
 *
 * The list is small and unpaginated, so one query serves the Concepts grid,
 * every picker and the Budget screen. Writes invalidate that single key plus the
 * record lists, because a rename or a delete changes what those rows show.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/preact-query";

import * as conceptsApi from "@/api/concepts";
import { STALE_TIME_MS, keys } from "@/api/queryKeys";
import type { Flow } from "@/types/api";

/** All live concepts for pickers. */
export function useConcepts(enabled = true) {
  return useQuery({
    queryKey: [...keys.concepts, "live"],
    queryFn: () => conceptsApi.fetchConcepts(),
    staleTime: STALE_TIME_MS,
    enabled,
  });
}

/** Live concepts of one flow, for the record form's picker. */
export function useConceptsByFlow(flow: Flow, enabled = true) {
  return useQuery({
    queryKey: [...keys.concepts, "live", flow],
    queryFn: () => conceptsApi.fetchConcepts({ flow }),
    staleTime: STALE_TIME_MS,
    enabled,
  });
}

/** Every concept including deleted ones, for the Concepts grid's toggle. */
export function useAllConcepts(enabled = true) {
  return useQuery({
    queryKey: [...keys.concepts, "all"],
    queryFn: () => conceptsApi.fetchConcepts({ includeDeleted: true }),
    staleTime: STALE_TIME_MS,
    enabled,
  });
}

function useInvalidateConceptData() {
  const client = useQueryClient();
  return () => {
    void client.invalidateQueries({ queryKey: keys.concepts });
    void client.invalidateQueries({ queryKey: ["records"] });
    void client.invalidateQueries({ queryKey: ["projections"] });
  };
}

/** Create a concept. */
export function useCreateConcept() {
  const invalidate = useInvalidateConceptData();
  return useMutation({
    mutationFn: (input: { name: string; flow: Flow }) =>
      conceptsApi.createConcept(input.name, input.flow),
    onSuccess: invalidate,
  });
}

/** Rename a concept. The UI confirms first: the change applies everywhere. */
export function useRenameConcept() {
  const invalidate = useInvalidateConceptData();
  return useMutation({
    mutationFn: (input: { id: number; name: string }) =>
      conceptsApi.renameConcept(input.id, input.name),
    onSuccess: invalidate,
  });
}

/** Soft-delete one concept. */
export function useDeleteConcept() {
  const invalidate = useInvalidateConceptData();
  return useMutation({
    mutationFn: (id: number) => conceptsApi.deleteConcept(id),
    onSuccess: invalidate,
  });
}

/** Bulk soft-delete from the multi-select. */
export function useBulkDeleteConcepts() {
  const invalidate = useInvalidateConceptData();
  return useMutation({
    mutationFn: (ids: number[]) => conceptsApi.deleteConcepts(ids),
    onSuccess: invalidate,
  });
}
