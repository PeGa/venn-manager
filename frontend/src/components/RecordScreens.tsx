/**
 * Home, Budget and History.
 *
 * Home and Budget operate on the user's working month, which only advances when
 * they confirm the switch (BACKEND.md § 1.4). History is the same grid, read
 * only, locked to a month picker.
 */
import { useState } from "preact/hooks";

import { ErrorNotice } from "./ErrorNotice";
import { RecordGrid } from "./RecordGrid";
import { SwitchCta, useMonthSwitch } from "./MonthSwitch";
import { Widgets } from "./Widgets";
import { useProjections } from "@/hooks/useProjections";
import { useSettings } from "@/hooks/useSettings";
import { useTranslation } from "@/hooks/useTranslation";
import { clampDateToMonth, historyMonths, previousMonth } from "@/utils/months";

/** Today as `YYYY-MM-DD`, in local time. */
function todayIso(): string {
  const now = new Date();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${now.getFullYear()}-${month}-${day}`;
}

export function HomeScreen() {
  const t = useTranslation();
  const monthSwitch = useMonthSwitch();
  const settings = useSettings(true);
  const workingMonth = monthSwitch.workingMonth;
  const projections = useProjections(workingMonth ?? "", workingMonth !== undefined);
  const currency = settings.data?.data.currency ?? "";

  return (
    <div class="space-y-4">
      <header class="flex flex-wrap items-center justify-between gap-2">
        <h2 class="text-lg font-semibold">{t("home_title")}</h2>
        <p class="text-sm text-muted" data-testid="working-month">
          {workingMonth ?? ""}
        </p>
        <SwitchCta />
      </header>

      {projections.error === null ? null : <ErrorNotice error={projections.error} />}
      <Widgets
        projections={projections.data?.data}
        currency={currency}
        loading={projections.isPending}
      />

      {workingMonth === undefined ? null : (
        <RecordGrid
          type="transaction"
          month={workingMonth}
          defaultDate={todayIso()}
          caption={t("home_title")}
        />
      )}
    </div>
  );
}

export function BudgetScreen() {
  const t = useTranslation();
  const monthSwitch = useMonthSwitch();
  const workingMonth = monthSwitch.workingMonth;

  return (
    <div class="space-y-4">
      <header class="flex flex-wrap items-center justify-between gap-2">
        <h2 class="text-lg font-semibold">{t("budget_title")}</h2>
        <SwitchCta />
      </header>
      <p class="text-sm text-muted">{t("budget_hint")}</p>

      <RecordGrid
        type="budget"
        defaultDate={todayIso()}
        caption={t("budget_title")}
        // FRONTEND.md § 2: the stored date is informational. It is displayed
        // inside the working month with the day clamped, never rewritten.
        displayDate={
          workingMonth === undefined
            ? undefined
            : (value) => clampDateToMonth(value, workingMonth)
        }
      />
    </div>
  );
}

export function HistoryScreen() {
  const t = useTranslation();
  const monthSwitch = useMonthSwitch();
  const state = monthSwitch.state;
  const workingMonth = monthSwitch.workingMonth;
  // null means "still showing the working month", which is what the screen
  // resets to on first entry (FRONTEND.md § 4).
  const [picked, setPicked] = useState<string | null>(null);

  const options = historyMonths(state?.earliest_month ?? null, workingMonth ?? "");
  const shown = picked ?? workingMonth ?? "";
  // Until the month state arrives there is no range to judge, so the "no history"
  // legend must not flash while the query is in flight.
  const loaded = state !== undefined && workingMonth !== undefined;
  const hasHistory = loaded && options.length > 0;

  return (
    <div class="space-y-4">
      <header>
        <h2 class="text-lg font-semibold">{t("history_title")}</h2>
        <p class="text-sm text-muted">{t("history_readonly_note")}</p>
      </header>

      <div class="vm-card flex flex-wrap items-end gap-3">
        <div>
          <label class="vm-label" for="history-month">
            {t("history_month_label")}
          </label>
          <input
            id="history-month"
            class="vm-input"
            type="month"
            value={picked ?? ""}
            min={options[0]}
            max={workingMonth === undefined ? undefined : previousMonth(workingMonth)}
            disabled={!hasHistory}
            data-testid="history-month"
            onChange={(event) => setPicked(event.currentTarget.value)}
          />
        </div>
        <p class="text-sm text-muted" data-testid="history-shown">
          {shown}
        </p>
        {hasHistory || !loaded ? null : (
          <p class="text-sm text-negative" data-testid="no-previous-months">
            {t("no_previous_months")}
          </p>
        )}
      </div>

      {shown === "" ? null : (
        <RecordGrid
          type="transaction"
          month={shown}
          readOnly
          defaultDate={shown}
          caption={t("history_title")}
        />
      )}
    </div>
  );
}
