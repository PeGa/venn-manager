/** Balance (FRONTEND.md § 5.6): the household's money, optionally per member. */
import { useQuery } from "@tanstack/solid-query";
import { For, Show } from "solid-js";

import { keys } from "@/adapters/queries";
import { formatMoney } from "@/domain/money";
import { Avatar, Skeleton } from "@/ui/components/basics";
import { useServices } from "@/ui/services";

export function BalanceScreen() {
  const { api, t, narrow } = useServices();
  const balance = useQuery(() => ({ queryKey: keys.balance, queryFn: () => api.balance() }));
  const household = useQuery(() => ({ queryKey: keys.household, queryFn: () => api.household() }));
  const money = (cents: number) => formatMoney(cents, household.data?.currencySign ?? "");
  const member = (id: string) => household.data?.members.find((m) => m.id === id);

  return (
    <Show when={balance.data} fallback={<Skeleton lines={3} />}>
      {(data) => (
        <div class="grid items-start gap-[18px]" classList={{ "grid-cols-[1fr_1.5fr]": !narrow(), "grid-cols-1 gap-2.5": narrow() }}>
          <section aria-label={t("balance_title")} class="rounded-card bg-primary p-6 text-on-primary">
            <p class="text-[13px] opacity-80">{t("balance_title")}</p>
            <p class="mt-1.5 font-mono text-[42px] font-medium tracking-[-1px]">{money(data().balance)}</p>
            <p class="mt-3 text-xs opacity-85">
              {t("balance_flows", { in: money(data().monthIn), out: money(data().monthOut) })}
            </p>
          </section>
          <Show when={data().members}>
            {(members) => (
              <section aria-label={t("member_income_title")} class="rounded-card border border-card-border bg-card px-[22px] py-2">
                <h2 class="py-3 font-bold">{t("member_income_title")}</h2>
                <ul>
                  <For each={members()}>
                    {(income) => {
                      const who = () => member(income.memberId);
                      const removed = () => who()?.status === "removed";
                      return (
                        <li class="flex items-center gap-3 border-t border-hairline py-[13px]">
                          <Avatar initial={who()?.initial ?? "?"} color={who()?.color ?? "#ddd"} dimmed={removed()} />
                          <b class="flex-1 text-sm" classList={{ "opacity-55": removed() }}>
                            {removed() ? t("tag_removed", { name: who()?.realName ?? "" }) : (who()?.realName ?? "")}
                          </b>
                          <span class="text-right text-xs text-muted">
                            <span class="block font-mono text-sm font-medium text-ink">{t("income_month", { amount: money(income.monthIn) })}</span>
                            {t("income_all_time", { amount: money(income.allTimeIn) })}
                          </span>
                        </li>
                      );
                    }}
                  </For>
                </ul>
              </section>
            )}
          </Show>
        </div>
      )}
    </Show>
  );
}
