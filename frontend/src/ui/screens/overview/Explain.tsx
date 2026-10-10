/**
 * The Explain dialog (FRONTEND.md § 5.1): every term of the forecast as rows,
 * so the reader can add up the hero figure themselves.
 */
import { useQuery } from "@tanstack/solid-query";
import { For, Show, type JSX } from "solid-js";

import { allPages, keys } from "@/adapters/queries";
import { dayLabel } from "@/domain/dates";
import { loggedTransactions, plannedLines } from "@/domain/forecast";
import type { Forecast, Member } from "@/domain/model";
import { formatMoney } from "@/domain/money";
import { Button, Skeleton } from "@/ui/components/basics";
import { Dialog } from "@/ui/components/Dialog";
import { useServices } from "@/ui/services";

const PAGE_SIZE = 200;

function Line(props: { title: string; subtitle?: string; amount: number; sign: string }) {
  return (
    <li class="flex items-center gap-3 border-t border-hairline py-2 text-sm">
      <span class="min-w-0 flex-1">
        <b class="block truncate font-semibold">{props.title}</b>
        <Show when={props.subtitle}>
          <span class="block truncate text-xs text-muted">{props.subtitle}</span>
        </Show>
      </span>
      <span
        class="font-mono font-medium"
        classList={{ "text-coral-text": props.amount < 0, "text-accent": props.amount > 0 }}
      >
        {formatMoney(props.amount, props.sign, { signed: true })}
      </span>
    </li>
  );
}

function Section(props: { label: string; value: string; children?: JSX.Element }) {
  return (
    <section aria-label={props.label} class="mt-4">
      <div class="flex items-baseline justify-between gap-3 pb-1.5">
        <h3 class="text-[13px] font-bold">{props.label}</h3>
        <span class="font-mono text-sm font-medium">{props.value}</span>
      </div>
      {props.children}
    </section>
  );
}

export function ExplainDialog(props: {
  forecast: Forecast;
  sign: string;
  today: string;
  members: Member[];
  onClose: () => void;
}) {
  const { api, t, language } = useServices();
  const budgets = useQuery(() => ({ queryKey: keys.budgets, queryFn: () => api.budgets() }));
  const transactions = useQuery(() => ({
    queryKey: keys.allTransactions,
    queryFn: () => allPages((page) => api.transactions({ page, size: PAGE_SIZE })),
  }));
  const money = (cents: number, signed = false) => formatMoney(cents, props.sign, { signed });
  const memberName = (id: string) => props.members.find((member) => member.id === id)?.realName ?? "";
  const empty = <li class="border-t border-hairline py-2 text-xs text-muted">{t("explain_empty")}</li>;

  return (
    <Dialog open title={t("explain_title")} onClose={() => props.onClose()}>
      <h2 class="text-[17px] font-bold">{t("explain_title")}</h2>
      <div class="max-h-[min(60vh,calc(100dvh_-_300px))] overflow-y-auto">
        <Section label={t("forecast_start")} value={money(props.forecast.startCash)} />
        <Show
          when={budgets.data && transactions.data}
          fallback={
            <Show when={budgets.isError || transactions.isError} fallback={<Skeleton lines={4} />}>
              <p class="mt-4 text-sm text-muted">{t("error_load")}</p>
            </Show>
          }
        >
          <Section
            label={t("forecast_logged", { n: props.forecast.transactionCount })}
            value={money(props.forecast.transactionsNet, true)}
          >
            <ul>
              <For each={loggedTransactions(transactions.data ?? [])} fallback={empty}>
                {(row) => (
                  <Line
                    title={row.category}
                    subtitle={`${memberName(row.memberId)} · ${dayLabel(language(), row.date, props.today)}`}
                    amount={row.amount}
                    sign={props.sign}
                  />
                )}
              </For>
            </ul>
          </Section>
          <Section label={t("forecast_planned")} value={money(props.forecast.planned, true)}>
            <ul>
              <For each={plannedLines(budgets.data?.items ?? [])} fallback={empty}>
                {(line) => <Line title={line.name} amount={line.remaining} sign={props.sign} />}
              </For>
            </ul>
          </Section>
        </Show>
      </div>
      <div class="mt-4 flex items-baseline justify-between border-t-2 border-ink pt-3">
        <b>{t("forecast_total")}</b>
        <span class="font-mono text-[22px] font-medium">{money(props.forecast.total)}</span>
      </div>
      <Button class="mt-4 w-full" onClick={() => props.onClose()}>
        {t("action_close")}
      </Button>
    </Dialog>
  );
}
