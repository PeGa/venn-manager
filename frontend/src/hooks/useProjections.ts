/**
 * Projection and month hooks (API_SURFACE.md § 5 and § 2).
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/preact-query";

import { fetchMonthState, fetchProjections, switchMonth } from "@/api/month";
import { MONTH_POLL_MS, STALE_TIME_MS, keys } from "@/api/queryKeys";

/** The five projection figures for one month. */
export function useProjections(month: string, enabled = true) {
  return useQuery({
    queryKey: keys.projections(month),
    queryFn: () => fetchProjections(month),
    staleTime: STALE_TIME_MS,
    enabled,
  });
}

/**
 * Month state, polled.
 *
 * FRONTEND.md § 2 and BACKEND.md § 3.5 require the frontend to notice a month
 * change on its own. Polling is the only mechanism the contracts allow — no
 * WebSocket, no SSE (AGENTS.md § What NOT to Do).
 */
export function useMonthState(enabled = true) {
  return useQuery({
    queryKey: keys.monthState,
    queryFn: fetchMonthState,
    staleTime: STALE_TIME_MS,
    refetchInterval: MONTH_POLL_MS,
    enabled,
  });
}

/**
 * Acknowledge the month change.
 *
 * Purely a state signal: no record moves. The projections and record lists are
 * invalidated anyway, because the working month decides whether a deleted
 * concept's rows are hidden or shown.
 */
export function useSwitchMonth() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: switchMonth,
    onSuccess: (result) => {
      client.setQueryData(keys.monthState, result);
      client.invalidateQueries({ queryKey: keys.settings });
      void client.invalidateQueries({ queryKey: ["records"] });
      void client.invalidateQueries({ queryKey: ["projections"] });
    },
  });
}
