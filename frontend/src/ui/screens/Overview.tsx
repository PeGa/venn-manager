/** Overview (FRONTEND.md § 5.1). */
import { A } from "@solidjs/router";
import { useQuery } from "@tanstack/solid-query";
import { For, Show, type JSX } from "solid-js";

import { keys } from "@/adapters/queries";
import { dueStatus } from "@/domain/dates";
import { formatMoney } from "@/domain/money";
import type { Forecast, Overview as OverviewData, UpcomingItem } from "@/domain/model";
import { ActivityList } from "@/ui/components/ActivityList";
import { Bar, Button, Card, CardTitle, Skeleton } from "@/ui/components/basics";
import { useServices } from "@/ui/services";

function Hero(props: { data: OverviewData }) {
  const { t, narrow } = useServices();
  const totals = () => props.data.budgetTotals;
  const money = (cents: number) => formatMoney(cents, props.data.currencySign, { decimals: 0 });
  const label = () => t(narrow() ? "overview_left_short" : "overview_left_long");
  return (
    <section aria-label={label()} class="rounded-card bg-primary text-on-primary" classList={{ "p-6": !narrow(), "px-5 py-[18px]": narrow() }}>
      <p class="text-[13px] opacity-80">{label()}</p>
      <p class="mt-1 font-mono font-medium tracking-[-1px]" classList={{ "text-[46px]": !narrow(), "text-[36px]": narrow() }}>
        {money(totals().leftToSpend)}
      </p>
      <div class="mt-4">
        <Bar pct={totals().spentPct} onDark label={label()} />
      </div>
      <p class="mt-2 text-xs opacity-85">
        {t(narrow() ? "overview_budgeted_short" : "overview_budgeted_long", {
          spent: money(totals().spent),
          limit: money(totals().limit),
        })}
      </p>
    </section>
  );
}

// Non-breaking spaces keep each operator with its number when the chip wraps.
const NBSP = "\u00a0";

export function formula(forecast: Forecast, sign: string): string {
  const money = (cents: number) => formatMoney(Math.abs(cents), sign);
  const term = (cents: number) => `${cents < 0 ? "−" : "+"}${NBSP}${money(cents)}`;
  const total = `=${NBSP}${formatMoney(forecast.total, sign)}`;
  return [formatMoney(forecast.startCash, sign), term(forecast.planned), term(forecast.transactionsNet), total].join(" ");
}

function ForecastCard(props: { forecast: Forecast; sign: string }) {
  const { t, narrow } = useServices();
  const money = (cents: number, signed = false) => formatMoney(cents, props.sign, { signed });
  const line = (label: string, value: string) => (
    <div class="flex justify-between border-b border-hairline py-2 text-sm">
      <span>{label}</span>
      <span class="font-mono">{value}</span>
    </div>
  );
  const title = () => t(narrow() ? "forecast_title_short" : "forecast_title_long");
  return (
    <section aria-label={title()} class="rounded-card border border-card-border bg-card" classList={{ "p-[22px]": !narrow(), "px-4 py-3.5": narrow() }}>
      <Show
        when={!narrow()}
        fallback={
          <div class="flex items-baseline justify-between">
            <h2 class="text-sm font-bold">{title()}</h2>
            <span class="font-mono text-[22px] font-medium text-primary dark:text-ink">{money(props.forecast.total)}</span>
          </div>
        }
      >
        <h2 class="font-bold">{title()}</h2>
        <p class="mb-3.5 mt-0.5 text-xs text-muted">{t("forecast_subtitle")}</p>
        <div class="flex flex-col gap-0.5">
          {line(t("forecast_start"), money(props.forecast.startCash))}
          {line(t("forecast_planned"), money(props.forecast.planned, true))}
          {line(t("forecast_logged", { n: props.forecast.transactionCount }), money(props.forecast.transactionsNet, true))}
        </div>
        <div class="mt-3.5 flex items-baseline justify-between">
          <b>{t("forecast_total")}</b>
          <span class="font-mono text-[30px] font-medium text-primary dark:text-ink">{money(props.forecast.total)}</span>
        </div>
      </Show>
      <p class="mt-2.5 rounded-control bg-highlight px-3 py-2.5 font-mono text-xs font-medium text-[#3c5a49] dark:text-accent">
        {formula(props.forecast, props.sign)}
      </p>
    </section>
  );
}

function UpcomingRow(props: { item: UpcomingItem; sign: string; today: string }) {
  const { language } = useServices();
  const month = () =>
    new Intl.DateTimeFormat(language(), { month: "short", timeZone: "UTC" })
      .format(new Date(`${props.item.dueDate}T00:00:00Z`))
      .replace(/\.$/, "")
      .toUpperCase();
  const money = (cents: number) => formatMoney(Math.abs(cents), props.sign, { decimals: 0 });
  const { t } = useServices();
  return (
    <li class="flex items-center gap-3 border-t border-hairline py-3">
      <span
        class="grid h-[38px] w-[38px] flex-none place-items-center rounded-xl text-center font-mono text-[11px] font-medium leading-tight"
        classList={{ "bg-coral-tint text-coral-text": props.item.soon, "bg-hairline text-ink": !props.item.soon }}
      >
        {month()}
        <br />
        {props.item.dueDate.slice(8)}
      </span>
      <span class="flex-1">
        <span class="block text-sm font-semibold">{props.item.name}</span>
        <span class="block text-xs" classList={{ "text-coral-text": props.item.soon, "text-muted": !props.item.soon }}>
          {dueStatus(language(), props.item.dueDate, props.today, props.item.overdue)}
        </span>
      </span>
      <span class="font-mono text-[15px] font-medium">
        {t("upcoming_amount", { actual: money(props.item.actual), amount: money(props.item.amount) })}
      </span>
    </li>
  );
}

function Panel(props: { label: string; aside?: JSX.Element; children: JSX.Element }) {
  const { narrow } = useServices();
  return (
    <section aria-label={props.label} class="rounded-card border border-card-border bg-card" classList={{ "px-[22px] py-5": !narrow(), "px-4 py-3": narrow() }}>
      <CardTitle aside={props.aside}>{props.label}</CardTitle>
      {props.children}
    </section>
  );
}

export function Overview() {
  const { api, t, narrow } = useServices();
  const overview = useQuery(() => ({ queryKey: keys.overview, queryFn: () => api.overview() }));
  const household = useQuery(() => ({ queryKey: keys.household, queryFn: () => api.household() }));

  return (
    <Show
      when={overview.data}
      fallback={
        <Show when={overview.isError} fallback={<Skeleton lines={4} />}>
          <Card>
            <p class="text-sm text-muted">{t("error_load")}</p>
            <Button class="mt-3" onClick={() => void overview.refetch()}>
              {t("action_retry")}
            </Button>
          </Card>
        </Show>
      }
    >
      {(data) => {
        const activity = () => (
          <Panel label={t("activity_title")} aside={<Show when={!narrow()}><span class="text-xs text-muted">{t("activity_caption")}</span></Show>}>
            <ActivityList
              entries={data().activity}
              members={household.data?.members ?? []}
              currencySign={data().currencySign}
              timezone={household.data?.timezone ?? "UTC"}
              today={data().period.today}
              compact={narrow()}
            />
          </Panel>
        );
        const upcoming = () => (
          <Panel
            label={t("upcoming_title")}
            aside={
              <A href="/budget" class="text-[13px] font-semibold text-accent">
                {t("upcoming_all")}
              </A>
            }
          >
            <ul class="mt-1.5">
              <For each={data().upcoming} fallback={<li class="py-3 text-xs text-muted">{t("upcoming_empty")}</li>}>
                {(item) => <UpcomingRow item={item} sign={data().currencySign} today={data().period.today} />}
              </For>
            </ul>
          </Panel>
        );
        return (
          <Show
            when={!narrow()}
            fallback={
              <div class="flex flex-col gap-2.5">
                <Hero data={data()} />
                <ForecastCard forecast={data().forecast} sign={data().currencySign} />
                {upcoming()}
                {activity()}
              </div>
            }
          >
            <div class="grid grid-cols-[1.1fr_1fr] gap-[18px]">
              <div class="flex flex-col gap-[18px]">
                <Hero data={data()} />
                {activity()}
              </div>
              <div class="flex flex-col gap-[18px] self-start">
                <ForecastCard forecast={data().forecast} sign={data().currencySign} />
                {upcoming()}
              </div>
            </div>
          </Show>
        );
      }}
    </Show>
  );
}
