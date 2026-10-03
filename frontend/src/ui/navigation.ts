/**
 * Where activity entries lead (FRONTEND.md § 7.2) and the highlight keys
 * records carry.
 */
import type { Section } from "@/domain/activity";
import type { ActivityTarget } from "@/domain/model";
import type { TranslationKey } from "@/l10n";

export const SECTION_PATH: Record<Section, string> = {
  overview: "/",
  budget: "/budget",
  transactions: "/transactions",
  history: "/history",
  goals: "/goals",
  balance: "/balance",
  settings: "/settings",
};

export const SECTION_LABEL: Record<Section, TranslationKey> = {
  overview: "nav_overview",
  budget: "nav_budget",
  transactions: "nav_transactions",
  history: "nav_history",
  goals: "nav_goals",
  balance: "nav_balance",
  settings: "nav_settings",
};

/** The highlight key of an activity target, or `null` for no target. */
export function targetKey(target: ActivityTarget): string | null {
  switch (target.type) {
    case "transaction":
      return `tx:${target.id}`;
    case "budget":
      return `budget:${target.id}`;
    case "member":
      return `member:${target.id}`;
    case "settings":
      return `settings:${target.section}`;
    case "none":
      return null;
  }
}

/** The URL an activity target opens. Archived transactions open their month. */
export function targetPath(target: ActivityTarget, section: Section): string {
  if (target.type === "transaction" && target.archived) {
    return `/history?month=${target.month}`;
  }
  return SECTION_PATH[section];
}
