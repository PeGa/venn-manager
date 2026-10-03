/**
 * Activity sentences and where an entry belongs (FRONTEND.md § 7).
 *
 * The server sends an action and parameters; the client words it, so the feed
 * follows the reader's language.
 */
import { formatMoney } from "@/domain/money";
import type { ActivityEntry } from "@/domain/model";
import { plural, translate, type Language, type TranslationKey } from "@/l10n";

export type Section =
  | "overview"
  | "budget"
  | "transactions"
  | "history"
  | "goals"
  | "balance"
  | "settings";

const SIMPLE: Partial<Record<ActivityEntry["action"], TranslationKey>> = {
  "tx.create": "act_tx_create",
  "tx.update": "act_tx_update",
  "tx.delete": "act_tx_delete",
  "budget.create": "act_budget_create",
  "budget.rename": "act_budget_rename",
  "budget.schedule": "act_budget_schedule",
  "budget.delete": "act_budget_delete",
  "member.invite": "act_member_invite",
  "member.update": "act_member_update",
  "member.remove": "act_member_remove",
  "settings.name": "act_settings_name",
  "settings.timezone": "act_settings_timezone",
};

/** What the actor did, e.g. `added “Greenfield Market”`. */
export function sentence(language: Language, entry: ActivityEntry, currencySign: string): string {
  const { action, params } = entry;
  const vars: Record<string, string | number> = {};
  for (const [name, value] of Object.entries(params)) {
    vars[name] = typeof value === "boolean" ? String(value) : value;
  }
  const simple = SIMPLE[action];
  if (simple !== undefined) {
    return translate(language, simple, vars);
  }
  const amount = Number(params["amount"] ?? 0);
  switch (action) {
    case "tx.bulkDelete":
      return plural(language, "act_tx_bulk_delete", Number(params["count"] ?? 0));
    case "budget.amount":
      return translate(language, "act_budget_amount", {
        ...vars,
        amount: formatMoney(amount, currencySign, { decimals: 0 }),
      });
    case "budget.goal":
      return translate(language, params["goal"] === true ? "act_budget_goal_on" : "act_budget_goal_off", vars);
    case "settings.currency":
      return params["sign"] === ""
        ? translate(language, "act_settings_currency_cleared")
        : translate(language, "act_settings_currency", vars);
    case "settings.openingBalance":
      return translate(language, "act_settings_opening_balance", {
        amount: formatMoney(amount, currencySign),
      });
    default:
      return translate(
        language,
        params["enabled"] === true ? "act_settings_member_income_on" : "act_settings_member_income_off",
      );
  }
}

/** The screen an entry belongs to: its target first, then its action. */
export function activitySection(entry: ActivityEntry): Section {
  const { target, action } = entry;
  if (target.type === "transaction") return target.archived ? "history" : "transactions";
  if (target.type === "budget") return target.goal ? "goals" : "budget";
  if (action.startsWith("tx.")) return "transactions";
  if (action.startsWith("budget.")) return "budget";
  return "settings";
}
