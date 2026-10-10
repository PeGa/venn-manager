/** Overview (FRONTEND.md § 5.1). */
import { A } from "@solidjs/router";
import { useQuery } from "@tanstack/solid-query";
import { createSignal, For, Show, type JSX } from "solid-js";

import { keys } from "@/adapters/queries";
import { dueStatus } from "@/domain/dates";
import { formatMoney } from "@/domain/money";
import type { Forecast, Member, Overview as OverviewData, UpcomingItem } from "@/domain/model";
import { ActivityList } from "@/ui/components/ActivityList";
import { Button, Card, CardTitle, Skeleton } from "@/ui/components/basics";
import { ExplainDialog } from "@/ui/screens/overview/Explain";
import { useServices } from "@/ui/services";

// Non-breaking spaces keep each operator with its number when the line wraps.
const NBSP = "\u00a0";

/** `{startCash} + {planned} + {transactionsNet} = {total}`, negative terms with `−`. */
export function formula(forecast: Forecast, sign: string): string {
  const money = (cents: number) => formatMoney(Math.abs(cents), sign);
  const term = (cents: number) => `${cents < 0 ? "−" : "+"}${NBSP}${money(cents)}`;
  const total = `=${NBSP}${formatMoney(forecast.total, sign)}`;
  return [formatMoney(forecast.startCash, sign), term(forecast.planned), term(forecast.transactionsNet), total].join(" ");
}

/** The month-end forecast: how much money the household will have (BACKEND.md § 4.4). */
function Hero(props: { data: OverviewData; members: Member[] }) {
  const { t, narrow } = useServices();
  const [explaining, setExplaining] = createSignal(false);
  const forecast = () => props.data.forecast;
  const money = (cents: number, signed = false) => formatMoney(cents, props.data.currencySign, { signed });
  const label = () => t(narrow() ? "forecast_title_short" : "forecast_title_long");
  const line = (name: string, value: string) => (
    <div class="flex justify-between border-b border-white/15 py-1.5 text-[13px]">
      <span class="opacity-85">{name}</span>
      <span class="font-mono">{value}</span>
    </div>
  );
  return (
    <section aria-label={label()} class="rounded-card bg-primary text-on-primary" classList={{ "p-6": !narrow(), "px-5 py-[18px]": narrow() }}>
      <p class="text-[13px] opacity-80">{label()}</p>
      <p class="mt-1 font-mono font-medium tracking-[-1px]" classList={{ "text-[46px]": !narrow(), "text-[36px]": narrow() }}>
        {money(forecast().total)}
      </p>
      <Show when={!narrow()}>
        <div class="mt-3 flex flex-col">
          {line(t("forecast_start"), money(forecast().startCash))}
          {line(t("forecast_planned"), money(forecast().planned, true))}
          {line(t("forecast_logged", { n: forecast().transactionCount }), money(forecast().transactionsNet, true))}
        </div>
      </Show>
      <p class="mt-3 rounded-control bg-white/10 px-3 py-2.5 font-mono text-xs font-medium">
        {formula(forecast(), props.data.currencySign)}
      </p>
      <p class="mt-2.5 flex items-center gap-2 text-xs">
        <span class="opacity-60">{t("explain_hint")}</span>
        <button type="button" onClick={() => setExplaining(true)} class="rounded-chip border border-white/30 px-2.5 py-1 font-semibold">
          {t("action_explain")}
        </button>
      </p>
      <Show when={explaining()}>
        <ExplainDialog
          forecast={forecast()}
          sign={props.data.currencySign}
          today={props.data.period.today}
          members={props.members}
          onClose={() => setExplaining(false)}
        />
      </Show>
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
                <Hero data={data()} members={household.data?.members ?? []} />
                {upcoming()}
                {activity()}
              </div>
            }
          >
            <div class="grid grid-cols-[1.1fr_1fr] gap-[18px]">
              <div class="flex flex-col gap-[18px]">
                <Hero data={data()} members={household.data?.members ?? []} />
                {activity()}
              </div>
              <div class="flex flex-col gap-[18px] self-start">
                {upcoming()}
              </div>
            </div>
          </Show>
        );
      }}
    </Show>
  );
}
