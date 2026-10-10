/**
 * Server-state bindings (FRONTEND.md § 8): query keys, the retry policy and
 * the client every screen shares.
 */
import { QueryCache, QueryClient } from "@tanstack/solid-query";

import type { Page } from "@/domain/model";
import { ApiError, type HistoryQuery } from "@/ports/api";

export const MAX_RETRIES = 3;

/** One place for every cache key, so invalidation stays obvious. */
export const keys = {
  session: ["session"] as const,
  household: ["household"] as const,
  overview: ["overview"] as const,
  budgets: ["budgets"] as const,
  transactions: (size: number) => ["transactions", size] as const,
  allTransactions: ["transactions", "all"] as const,
  balance: ["balance"] as const,
  facets: ["history", "facets"] as const,
  months: (filters: HistoryQuery) => ["history", "months", filters] as const,
  monthTransactions: (month: string, filters: HistoryQuery) =>
    ["history", "transactions", month, filters] as const,
  breakdown: (month: string, filters: HistoryQuery) =>
    ["history", "breakdown", month, filters] as const,
};

/** Every item of a paged list, reading page 1, 2, … until the total is reached. */
export async function allPages<T>(fetchPage: (page: number) => Promise<Page<T>>): Promise<T[]> {
  const items: T[] = [];
  for (let page = 1; ; page++) {
    const { items: batch, total } = await fetchPage(page);
    items.push(...batch);
    if (batch.length === 0 || items.length >= total) return items;
  }
}

/** Retry network and server failures only. A 4xx will not fix itself. */
export function shouldRetry(failures: number, error: unknown): boolean {
  if (failures >= MAX_RETRIES) {
    return false;
  }
  return !(error instanceof ApiError) || error.status === 0 || error.status >= 500;
}

/** Called when any query fails, with that query's key. */
export type QueryErrorHook = (error: unknown, queryKey: readonly unknown[]) => void;

/** The app's query client: refetch on focus, never on a timer. */
export function createQueryClient(onError?: QueryErrorHook): QueryClient {
  return new QueryClient({
    queryCache: new QueryCache(
      onError === undefined ? {} : { onError: (error, query) => onError(error, query.queryKey) },
    ),
    defaultOptions: {
      queries: {
        retry: shouldRetry,
        staleTime: 0,
        refetchOnWindowFocus: true,
        refetchInterval: false,
      },
      mutations: { retry: false },
    },
  });
}
