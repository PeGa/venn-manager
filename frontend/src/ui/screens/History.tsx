/** History (FRONTEND.md § 5.4): read-only past months with server-side filters. */
import { useSearchParams } from "@solidjs/router";
import { keepPreviousData, useInfiniteQuery, useQuery } from "@tanstack/solid-query";
import { createSignal, For, onCleanup, Show } from "solid-js";

import { keys } from "@/adapters/queries";
import { localDate } from "@/domain/dates";
import type { HistoryQuery } from "@/ports/api";
import { Button, Chip, Skeleton } from "@/ui/components/basics";
import { BreakdownDialog } from "@/ui/screens/history/Breakdown";
import { MonthGroup } from "@/ui/screens/history/MonthGroup";
import { useServices } from "@/ui/services";

export const MONTHS_PER_PAGE = 12;
export const SEARCH_DELAY_MS = 300;

function ChipRow(props: { label: string; options: { id: string; label: string }[]; value: string | undefined; pick: (id: string | undefined) => void }) {
  const { t } = useServices();
  return (
    <div role="group" aria-label={props.label} class="flex flex-wrap items-center gap-1.5">
      <span class="w-[54px] flex-none text-[11px] text-muted">{props.label}</span>
      <Chip active={props.value === undefined} onClick={() => props.pick(undefined)}>
        {t("filter_all")}
      </Chip>
      <For each={props.options}>
        {(option) => (
          <Chip active={props.value === option.id} onClick={() => props.pick(option.id)}>
            {option.label}
          </Chip>
        )}
      </For>
    </div>
  );
}

export function History() {
  const { api, t } = useServices();
  const [params] = useSearchParams();
  const [search, setSearch] = createSignal("");
  const [query, setQuery] = createSignal("");
  const [memberId, setMemberId] = createSignal<string | undefined>();
  const [budgetId, setBudgetId] = createSignal<string | undefined>();
  const [details, setDetails] = createSignal<string | null>(null);
  let timer: ReturnType<typeof setTimeout> | undefined;
  onCleanup(() => clearTimeout(timer));

  const filters = (): HistoryQuery => {
    const result: HistoryQuery = {};
    if (query() !== "") result.q = query();
    const member = memberId();
    if (member !== undefined) result.memberId = member;
    const budget = budgetId();
    if (budget !== undefined) result.budgetId = budget;
    return result;
  };
  const filtered = () => Object.keys(filters()).length > 0;

  const household = useQuery(() => ({ queryKey: keys.household, queryFn: () => api.household() }));
  const facets = useQuery(() => ({ queryKey: keys.facets, queryFn: () => api.historyFacets() }));
  const months = useInfiniteQuery(() => ({
    queryKey: keys.months(filters()),
    queryFn: ({ pageParam }) => api.historyMonths({ ...filters(), page: pageParam, size: MONTHS_PER_PAGE }),
    initialPageParam: 1,
    getNextPageParam: (last) => (last.page * last.size < last.total ? last.page + 1 : undefined),
    // Keep showing the current months while filtered ones load, instead of suspending.
    placeholderData: keepPreviousData,
  }));
  const list = () => months.data?.pages.flatMap((page) => page.items) ?? [];
  const today = () => localDate(new Date().toISOString(), household.data?.timezone ?? "UTC");
  const currencySign = () => household.data?.currencySign ?? "";

  const typeSearch = (value: string) => {
    setSearch(value);
    clearTimeout(timer);
    timer = setTimeout(() => setQuery(value.trim()), SEARCH_DELAY_MS);
  };
  const clear = () => {
    clearTimeout(timer);
    setSearch("");
    setQuery("");
    setMemberId(undefined);
    setBudgetId(undefined);
  };
  // Arriving from an activity entry: start with no filters so the target is visible.
  if (typeof params["month"] === "string") clear();

  return (
    <div class="flex flex-col gap-4">
      <div class="flex flex-col gap-2.5 rounded-2xl border border-card-border bg-card px-3.5 py-3">
        <div class="flex items-center gap-2">
          <input
            aria-label={t("history_search")}
            placeholder={t("history_search")}
            value={search()}
            onInput={(event) => typeSearch(event.currentTarget.value)}
            class="min-w-0 flex-1 rounded-control border border-input-border bg-input-bg px-3 py-2.5 text-[13px]"
          />
          <button
            type="button"
            onClick={clear}
            class="rounded-control border border-input-border bg-card px-3 py-[9px] text-xs font-semibold"
            classList={{ "text-coral-text": filtered() || search() !== "", "text-disabled-text": !filtered() && search() === "" }}
          >
            {t("action_clear")}
          </button>
        </div>
        <ChipRow
          label={t("filter_member")}
          options={(facets.data?.members ?? []).map((m) => ({ id: m.id, label: m.status === "removed" ? t("tag_removed", { name: m.realName }) : m.realName }))}
          value={memberId()}
          pick={setMemberId}
        />
        <ChipRow
          label={t("filter_category")}
          options={(facets.data?.categories ?? []).map((c) => ({ id: c.budgetId, label: c.deleted ? t("tag_deleted", { name: c.name }) : c.name }))}
          value={budgetId()}
          pick={setBudgetId}
        />
      </div>
      <Show when={months.data} fallback={<Skeleton lines={4} />}>
        <For
          each={list()}
          fallback={
            <p class="p-6 text-center text-[13px] text-muted">{t(filtered() ? "history_no_match" : "history_empty")}</p>
          }
        >
          {(month) => (
            <MonthGroup
              month={month}
              filters={filters()}
              members={household.data?.members ?? []}
              currencySign={currencySign()}
              today={today()}
              filtered={filtered()}
              onDetails={() => setDetails(month.month)}
            />
          )}
        </For>
        <Show when={months.hasNextPage}>
          <Button onClick={() => void months.fetchNextPage()}>{t("action_earlier_months")}</Button>
        </Show>
      </Show>
      <Show when={details()}>
        {(month) => <BreakdownDialog month={month()} filters={filters()} currencySign={currencySign()} onClose={() => setDetails(null)} />}
      </Show>
    </div>
  );
}
