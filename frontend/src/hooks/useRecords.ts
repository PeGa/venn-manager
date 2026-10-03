/**
 * Record hooks (API_SURFACE.md § 4).
 *
 * One query per (type, month, page, size, search) tuple. Writing a record
 * invalidates the record lists, the projections that depend on them, and the
 * month state — because `earliest_month` is derived from the oldest transaction.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/preact-query";

import * as recordsApi from "@/api/records";
import { STALE_TIME_MS, keys } from "@/api/queryKeys";
import type {
  MoneyRecord,
  PageSize,
  RecordCreateInput,
  RecordType,
  RecordUpdateInput,
} from "@/types/api";

export interface RecordListParams {
  type: RecordType;
  month?: string;
  page: number;
  size: PageSize;
  search: string;
}

/** A page of records plus its pagination meta. */
export function useRecords(params: RecordListParams, enabled = true) {
  return useQuery({
    queryKey: keys.records({
      type: params.type,
      month: params.month,
      page: params.page,
      size: params.size,
      search: params.search,
    }),
    queryFn: () =>
      recordsApi.fetchRecords({
        type: params.type,
        month: params.month,
        page: params.page,
        q: params.size,
        search: params.search,
      }),
    staleTime: STALE_TIME_MS,
    enabled,
  });
}

/** Invalidate everything a record write can move. */
function useInvalidateRecordData() {
  const client = useQueryClient();
  return () => {
    void client.invalidateQueries({ queryKey: ["records"] });
    void client.invalidateQueries({ queryKey: ["projections"] });
    void client.invalidateQueries({ queryKey: keys.monthState });
  };
}

/** Create a transaction or a budget. */
export function useCreateRecord() {
  const invalidate = useInvalidateRecordData();
  return useMutation({
    mutationFn: (input: RecordCreateInput) => recordsApi.createRecord(input),
    onSuccess: invalidate,
  });
}

/** Partially update a record. A 410 means someone else deleted it first. */
export function useUpdateRecord() {
  const invalidate = useInvalidateRecordData();
  return useMutation({
    mutationFn: (input: { id: number; type: RecordType; patch: RecordUpdateInput }) =>
      recordsApi.updateRecord(input.id, input.type, input.patch),
    onSuccess: invalidate,
  });
}

/** Soft-delete one record. */
export function useDeleteRecord() {
  const invalidate = useInvalidateRecordData();
  return useMutation({
    mutationFn: (input: { id: number; type: RecordType }) =>
      recordsApi.deleteRecord(input.id, input.type),
    onSuccess: invalidate,
  });
}

/** Bulk soft-delete, all-or-nothing. */
export function useBulkDeleteRecords() {
  const invalidate = useInvalidateRecordData();
  return useMutation({
    mutationFn: (input: { ids: number[]; type: RecordType }) =>
      recordsApi.deleteRecords(input.ids, input.type),
    onSuccess: () => invalidate(),
  });
}

/** Narrow a record list to the ids a screen has selected. */
export function selectedIds(records: MoneyRecord[], selection: ReadonlySet<number>): number[] {
  return records.filter((record) => selection.has(record.id)).map((record) => record.id);
}
