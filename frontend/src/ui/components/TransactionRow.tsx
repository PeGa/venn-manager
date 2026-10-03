/** One transaction (FRONTEND.md § 4.1). Wide: columns. Narrow: a compact card. */
import { Show, type JSX } from "solid-js";

import { dayLabel } from "@/domain/dates";
import type { Member, Transaction } from "@/domain/model";
import { formatMoney } from "@/domain/money";
import { Avatar } from "@/ui/components/basics";
import { useServices } from "@/ui/services";

export function TransactionRow(props: {
  transaction: Transaction;
  member: Member | undefined;
  currencySign: string;
  today: string;
  selected?: boolean;
  /** Replaces the avatar, e.g. with a check mark in touch select mode. */
  badge?: JSX.Element;
}) {
  const { t, language, narrow } = useServices();
  const removed = () => props.member?.status === "removed";
  const memberName = () =>
    removed() ? t("tag_removed", { name: props.member?.realName ?? "" }) : (props.member?.realName ?? "");
  const category = () =>
    props.transaction.categoryDeleted ? t("tag_deleted", { name: props.transaction.category }) : props.transaction.category;
  const day = () => dayLabel(language(), props.transaction.date, props.today);
  const amount = () => formatMoney(props.transaction.amount, props.currencySign, { signed: true });

  return (
    <div
      class="flex items-center"
      classList={{
        "gap-3.5 py-[11px]": !narrow(),
        "gap-2.5 py-0.5": narrow(),
        "opacity-55": props.transaction.categoryDeleted,
      }}
    >
      <Show when={props.badge} fallback={<Avatar initial={props.member?.initial ?? "?"} color={props.member?.color ?? "#ddd"} size={narrow() ? 30 : 34} dimmed={removed()} />}>
        {props.badge}
      </Show>
      <span class="min-w-0 flex-1" classList={{ "text-sm": !narrow(), "text-[13px]": narrow() }}>
        <b class="block truncate">{props.transaction.payee}</b>
        <span class="block truncate text-muted" classList={{ "text-xs": !narrow(), "text-[11px]": narrow() }}>
          {narrow() ? `${category()} · ${day()}` : `${memberName()} · ${day()}`}
        </span>
      </span>
      <Show when={!narrow()}>
        <span class="w-[130px] truncate text-[13px] text-muted">{category()}</span>
      </Show>
      <span
        class="text-right font-mono font-medium"
        classList={{
          "w-[120px] text-sm": !narrow(),
          "text-[13px]": narrow(),
          "text-accent": props.transaction.amount > 0,
        }}
      >
        {amount()}
      </span>
    </div>
  );
}
