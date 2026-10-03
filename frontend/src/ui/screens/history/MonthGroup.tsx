/** One past month: totals, Details…, and its rows (FRONTEND.md § 5.4). */
import { keepPreviousData, useInfiniteQuery } from "@tanstack/solid-query";
import { For, Show } from "solid-js";

import { keys } from "@/adapters/queries";
import { monthTitle } from "@/domain/dates";
import type { HistoryMonth, Member } from "@/domain/model";
import { formatMoney } from "@/domain/money";
import type { HistoryQuery } from "@/ports/api";
import { Button } from "@/ui/components/basics";
import { Highlight } from "@/ui/components/Highlight";
import { TransactionRow } from "@/ui/components/TransactionRow";
import { useServices } from "@/ui/services";

export const MONTH_ROWS = 200;

export function MonthGroup(props: {
  month: HistoryMonth;
  filters: HistoryQuery;
  members: Member[];
  currencySign: string;
  today: string;
  filtered: boolean;
  onDetails: () => void;
}) {
  const { api, t, p, language, narrow } = useServices();
  const rows = useInfiniteQuery(() => ({
    queryKey: keys.monthTransactions(props.month.month, props.filters),
    queryFn: ({ pageParam }) =>
      api.historyTransactions(props.month.month, { ...props.filters, page: pageParam, size: MONTH_ROWS }),
    initialPageParam: 1,
    getNextPageParam: (last) => (last.page * last.size < last.total ? last.page + 1 : undefined),
    placeholderData: keepPreviousData,
  }));
  const money = (cents: number) => formatMoney(cents, props.currencySign, { decimals: 0 });
  const title = () => monthTitle(language(), props.month.month);
  const count = () =>
    props.month.matchCount === props.month.totalCount
      ? p("transactions_count", props.month.totalCount)
      : t("transactions_partial", { n: props.month.matchCount, total: props.month.totalCount });
  const member = (id: string) => props.members.find((m) => m.id === id);

  return (
    <section aria-label={title()} class="rounded-[20px] border border-card-border bg-card" classList={{ "px-[22px] py-[18px]": !narrow(), "px-4 py-3.5": narrow() }}>
      <header class="flex flex-wrap items-center gap-x-[22px] gap-y-2 pb-3">
        <div class="flex-1">
          <h2 class="text-[17px] font-bold">{title()}</h2>
          <p class="text-xs text-muted">
            {count()} · {t("read_only")}
          </p>
        </div>
        <div class="text-right">
          <p class="text-[11px] text-muted">{t("history_spent")}</p>
          <p class="font-mono text-base font-medium">{money(props.month.spent)}</p>
        </div>
        <div class="text-right">
          <p class="text-[11px] text-muted">{t("history_earned")}</p>
          <p class="font-mono text-base font-medium text-accent">{money(props.month.earned)}</p>
        </div>
        <Button small onClick={() => props.onDetails()} class="bg-input-bg text-primary dark:text-ink">
          {t("action_details")}
        </Button>
      </header>
      <ul>
        <For each={rows.data?.pages.flatMap((page) => page.items) ?? []}>
          {(row) => (
            <li class="border-t border-hairline">
              <Highlight key={`tx:${row.id}`} class="rounded-control">
                <TransactionRow transaction={row} member={member(row.memberId)} currencySign={props.currencySign} today={props.today} />
              </Highlight>
            </li>
          )}
        </For>
      </ul>
      <Show when={rows.hasNextPage}>
        <Button small onClick={() => void rows.fetchNextPage()}>
          {t("action_show_more")}
        </Button>
      </Show>
    </section>
  );
}
