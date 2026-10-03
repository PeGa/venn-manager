/** Household name, time zone, opening balance and member income (FRONTEND.md § 5.7). */
import { createSignal, For } from "solid-js";

import type { Household } from "@/domain/model";
import { parseAmount } from "@/domain/money";
import type { HouseholdChanges } from "@/ports/api";
import { Field } from "@/ui/components/basics";
import { SettingsCard } from "@/ui/screens/settings/SettingsCard";
import { useServices } from "@/ui/services";

const ZONES = Intl.supportedValuesOf("timeZone");

/**
 * The time zones to offer. Browsers list canonical zones only, so aliases the
 * server accepts (such as `UTC`) are kept by adding the current one first.
 */
export function zoneOptions(current: string, zones: readonly string[] = ZONES): readonly string[] {
  return zones.includes(current) ? zones : [current, ...zones];
}

export function HouseholdCard(props: { household: Household; save: (changes: HouseholdChanges) => void }) {
  const { t } = useServices();
  const [name, setName] = createSignal<string | null>(null);
  const [balance, setBalance] = createSignal<string | null>(null);
  const [balanceError, setBalanceError] = createSignal<string | undefined>();

  const commitName = () => {
    const value = name()?.trim();
    setName(null);
    if (value !== undefined && value !== "" && value !== props.household.name) props.save({ name: value });
  };
  const commitBalance = () => {
    const text = balance();
    if (text === null) return;
    const cents = parseAmount(text);
    if (cents === null) {
      setBalanceError(t("error_amount"));
      return;
    }
    setBalance(null);
    setBalanceError(undefined);
    if (cents !== props.household.openingBalance) props.save({ openingBalance: cents });
  };
  const onEnter = (commit: () => void) => (event: KeyboardEvent) => {
    if (event.key === "Enter") commit();
  };

  return (
    <SettingsCard section="household" title={t("household_title")} subtitle={t("household_subtitle")}>
      <div class="flex flex-col gap-3.5">
        <Field
          label={t("field_household_name")}
          maxLength={60}
          value={name() ?? props.household.name}
          onInput={(event) => setName(event.currentTarget.value)}
          onBlur={commitName}
          onKeyDown={onEnter(commitName)}
        />
        <label class="flex flex-col gap-1 text-xs font-semibold text-muted">
          {t("field_timezone")}
          <select
            value={props.household.timezone}
            onChange={(event) => props.save({ timezone: event.currentTarget.value })}
            class="rounded-control border border-input-border bg-input-bg px-3 py-2.5 text-sm font-normal text-ink"
          >
            <For each={zoneOptions(props.household.timezone)}>{(zone) => <option value={zone}>{zone}</option>}</For>
          </select>
        </label>
        <Field
          label={t("field_opening_balance")}
          mono
          inputmode="decimal"
          value={balance() ?? String(props.household.openingBalance / 100)}
          error={balanceError()}
          onInput={(event) => setBalance(event.currentTarget.value)}
          onBlur={commitBalance}
          onKeyDown={onEnter(commitBalance)}
        />
        <p class="-mt-2 text-xs text-muted">{t("opening_balance_hint")}</p>
        <div class="flex items-start gap-2">
          <input
            id="member-income"
            type="checkbox"
            aria-describedby="member-income-hint"
            checked={props.household.showMemberIncome}
            onChange={(event) => props.save({ showMemberIncome: event.currentTarget.checked })}
            class="mt-0.5 h-4 w-4 accent-[var(--accent)]"
          />
          <div>
            <label for="member-income" class="text-sm font-semibold">
              {t("member_income_label")}
            </label>
            <p id="member-income-hint" class="text-xs text-muted">
              {t("member_income_hint")}
            </p>
          </div>
        </div>
      </div>
    </SettingsCard>
  );
}
