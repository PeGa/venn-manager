/** Currency sign: display only, 0–8 characters (FRONTEND.md § 5.7). */
import { createSignal, For, onCleanup } from "solid-js";

import type { Household } from "@/domain/model";
import { Chip, Field } from "@/ui/components/basics";
import { SAVE_DELAY_MS } from "@/ui/components/BudgetCard";
import { SettingsCard } from "@/ui/screens/settings/SettingsCard";
import { useServices } from "@/ui/services";

const QUICK = ["$", "€", "£", "¥"] as const;
export const CURRENCY_SIGN_MAX = 8;

export function CurrencyCard(props: { household: Household; save: (sign: string) => void }) {
  const { t } = useServices();
  const [typed, setTyped] = createSignal<string | null>(null);
  let timer: ReturnType<typeof setTimeout> | undefined;
  onCleanup(() => clearTimeout(timer));
  const value = () => typed() ?? props.household.currencySign;

  const type = (sign: string) => {
    setTyped(sign);
    clearTimeout(timer);
    timer = setTimeout(() => {
      props.save(sign.trim());
      setTyped(null);
    }, SAVE_DELAY_MS);
  };

  return (
    <SettingsCard section="currency" title={t("currency_title")} subtitle={t("currency_subtitle")}>
      <Field
        label={t("currency_title")}
        hideLabel
        mono
        maxLength={CURRENCY_SIGN_MAX}
        value={value()}
        onInput={(event) => type(event.currentTarget.value)}
      />
      <div class="mt-2.5 flex gap-2">
        <For each={QUICK}>
          {(sign) => (
            <Chip mono active={value() === sign} onClick={() => props.save(sign)}>
              {sign}
            </Chip>
          )}
        </For>
      </div>
    </SettingsCard>
  );
}
