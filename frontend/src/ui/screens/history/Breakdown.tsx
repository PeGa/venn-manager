/** The "Details…" dialog: spending by category for one month (FRONTEND.md § 5.4). */
import { useQuery } from "@tanstack/solid-query";
import { For, Show } from "solid-js";

import { keys } from "@/adapters/queries";
import { monthTitle } from "@/domain/dates";
import { formatMoney } from "@/domain/money";
import { pieSegments } from "@/domain/pie";
import type { HistoryQuery } from "@/ports/api";
import { Button } from "@/ui/components/basics";
import { Dialog } from "@/ui/components/Dialog";
import { useServices } from "@/ui/services";

// A circle of this radius has a circumference of 100, so dash lengths are percentages.
const RADIUS = 15.9155;

export function BreakdownDialog(props: { month: string; filters: HistoryQuery; currencySign: string; onClose: () => void }) {
  const { api, t, language } = useServices();
  const breakdown = useQuery(() => ({
    queryKey: keys.breakdown(props.month, props.filters),
    queryFn: () => api.historyBreakdown(props.month, props.filters),
  }));
  const money = (cents: number) => formatMoney(cents, props.currencySign, { decimals: 0 });
  const title = () => monthTitle(language(), props.month);
  const segments = () => pieSegments(breakdown.data?.slices.map((slice) => slice.amount) ?? []);

  return (
    <Dialog open title={title()} onClose={() => props.onClose()}>
      <b class="text-[17px]">{title()}</b>
      <Show when={breakdown.data}>
        {(data) => (
          <>
            <p class="mb-3.5 mt-0.5 text-xs text-muted">
              {t("breakdown_totals", { spent: money(data().spent), earned: money(data().earned) })}
            </p>
            <div class="flex items-center gap-5">
              <svg viewBox="0 0 42 42" class="h-[150px] w-[150px] flex-none -rotate-90" aria-hidden="true">
                <circle cx="21" cy="21" r={RADIUS} fill="none" stroke="var(--hairline)" stroke-width="21" />
                <For each={segments()}>
                  {(segment) => (
                    <circle
                      cx="21"
                      cy="21"
                      r={RADIUS}
                      fill="none"
                      stroke={segment.color}
                      stroke-width="21"
                      stroke-dasharray={`${String(segment.length)} ${String(100 - segment.length)}`}
                      stroke-dashoffset={String(-segment.start)}
                    />
                  )}
                </For>
              </svg>
              <ul class="flex flex-1 flex-col gap-[7px]">
                <For each={data().slices}>
                  {(slice, index) => (
                    <li class="flex items-center gap-2 text-[13px]">
                      <span class="h-2.5 w-2.5 flex-none rounded-[3px]" style={{ background: segments()[index()]?.color }} />
                      <span class="flex-1">{slice.category}</span>
                      <span class="font-mono text-xs font-medium">{money(slice.amount)}</span>
                      <span class="w-[34px] text-right font-mono text-[11px] font-medium text-faint">{`${String(slice.pct)}%`}</span>
                    </li>
                  )}
                </For>
              </ul>
            </div>
          </>
        )}
      </Show>
      <Button class="mt-4 w-full" onClick={() => props.onClose()}>
        {t("action_close")}
      </Button>
    </Dialog>
  );
}
