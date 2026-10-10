/**
 * Transactions (FRONTEND.md § 5.3, § 6): the add bar, this month's rows,
 * selection by mouse or touch, inline or sheet editing, and removal.
 */
import { useInfiniteQuery, useQuery } from "@tanstack/solid-query";
import { createMemo, createSignal, For, onCleanup, Show } from "solid-js";

import { keys } from "@/adapters/queries";
import { localDate } from "@/domain/dates";
import type { Transaction } from "@/domain/model";
import { formatMoney } from "@/domain/money";
import { click, EMPTY, prune, toggle, type Selection } from "@/domain/selection";
import type { NewTransaction, TransactionChanges } from "@/ports/api";
import { Button, Skeleton } from "@/ui/components/basics";
import { ConfirmDialog } from "@/ui/components/ConfirmDialog";
import { Dialog } from "@/ui/components/Dialog";
import { Highlight } from "@/ui/components/Highlight";
import { TransactionRow } from "@/ui/components/TransactionRow";
import { useNotice, useRefresh } from "@/ui/errors";
import { AddBar } from "@/ui/screens/transactions/AddBar";
import { EditForm } from "@/ui/screens/transactions/EditForm";
import { useServices } from "@/ui/services";

export const PAGE_SIZE = 200;
export const LONG_PRESS_MS = 450;

export function Transactions() {
  const { api, t, coarse, narrow } = useServices();
  const pages = useInfiniteQuery(() => ({
    queryKey: keys.transactions(PAGE_SIZE),
    queryFn: ({ pageParam }) => api.transactions({ page: pageParam, size: PAGE_SIZE }),
    initialPageParam: 1,
    getNextPageParam: (last) => (last.page * last.size < last.total ? last.page + 1 : undefined),
  }));
  const budgets = useQuery(() => ({ queryKey: keys.budgets, queryFn: () => api.budgets() }));
  const household = useQuery(() => ({ queryKey: keys.household, queryFn: () => api.household() }));
  const notice = useNotice();
  const refresh = useRefresh();

  const rows = createMemo(() => pages.data?.pages.flatMap((page) => page.items) ?? []);
  const selectable = () => rows().filter((row) => !row.categoryDeleted).map((row) => row.id);
  const [rawSelection, setSelection] = createSignal<Selection>(EMPTY);
  const selection = () => prune(rawSelection(), selectable());
  const [editing, setEditing] = createSignal<Transaction | null>(null);
  const [menu, setMenu] = createSignal<{ ids: string[]; title: string } | null>(null);
  const [confirming, setConfirming] = createSignal<string[] | null>(null);
  const today = () => localDate(new Date().toISOString(), household.data?.timezone ?? "UTC");
  const member = (id: string) => household.data?.members.find((m) => m.id === id);
  const byId = (id: string) => rows().find((row) => row.id === id);

  const add = (transaction: NewTransaction) =>
    api.createTransaction(transaction).then(refresh).then(() => true, (error: unknown) => {
      notice.report(error);
      return false;
    });
  const save = (id: string, changes: TransactionChanges) => {
    setEditing(null);
    void api.updateTransaction(id, changes).then(refresh).catch(notice.report);
  };
  const remove = (ids: string[]) => {
    setMenu(null);
    setConfirming(null);
    setSelection(EMPTY);
    const call = ids.length === 1 ? api.deleteTransaction(ids[0] ?? "") : api.bulkDeleteTransactions(ids);
    void call.then(refresh).catch(notice.report);
  };
  const askRemove = (ids: string[]) => (ids.length > 1 ? setConfirming(ids) : remove(ids));

  // Touch: long press enters select mode; a tap opens the action sheet.
  let pressTimer: ReturnType<typeof setTimeout> | undefined;
  let longPressed = false;
  onCleanup(() => clearTimeout(pressTimer));
  const startPress = (row: Transaction) => {
    longPressed = false;
    clearTimeout(pressTimer);
    pressTimer = setTimeout(() => {
      longPressed = true;
      const current = selection();
      if (current.ids.length > 0 && current.ids.includes(row.id)) {
        setMenu({ ids: [...current.ids], title: t("selected_count", { n: current.ids.length }) });
      } else {
        setSelection(toggle(current, row.id));
      }
    }, LONG_PRESS_MS);
  };
  const endPress = () => clearTimeout(pressTimer);

  const menuTitle = (row: Transaction) =>
    `${row.category} · ${formatMoney(row.amount, household.data?.currencySign ?? "", { signed: true })}`;

  const activate = (row: Transaction, event: MouseEvent | KeyboardEvent) => {
    if (row.categoryDeleted) return;
    if (coarse()) {
      if (longPressed) {
        longPressed = false;
        return;
      }
      if (selection().ids.length > 0) setSelection(toggle(selection(), row.id));
      else setMenu({ ids: [row.id], title: menuTitle(row) });
      return;
    }
    setEditing(null);
    setSelection(click(selection(), selectable(), row.id, { shift: event.shiftKey, toggle: event.ctrlKey || event.metaKey }));
  };

  const selectedCount = () => selection().ids.length;
  const onlySelected = () => (selectedCount() === 1 ? byId(selection().ids[0] ?? "") : undefined);

  return (
    <div class="flex flex-col" classList={{ "gap-3.5": !narrow(), "gap-2.5": narrow() }}>
      {notice.view()}
      <AddBar budgets={budgets.data?.items ?? []} add={add} />
      <Show when={coarse() && selectedCount() > 0}>
        <div class="flex items-center gap-2 rounded-[14px] bg-primary py-2 pl-3.5 pr-2 text-[13px] text-white">
          <b class="flex-1">{t("selected_count", { n: selectedCount() })}</b>
          <button type="button" class="rounded-[9px] bg-coral-tint px-3 py-[7px] text-xs font-semibold text-coral-text" onClick={() => askRemove([...selection().ids])}>
            {t("action_remove")}
          </button>
          <button type="button" class="rounded-[9px] bg-white/20 px-3 py-[7px] text-xs font-semibold" onClick={() => setSelection(EMPTY)}>
            {t("action_done")}
          </button>
        </div>
      </Show>
      <Show when={pages.data} fallback={<Skeleton lines={5} />}>
        <div
          role="listbox"
          aria-label={t("nav_transactions")}
          aria-multiselectable="true"
          classList={{ "rounded-[18px] border border-card-border bg-card px-5 py-1.5": !narrow(), "flex flex-col gap-2": narrow() }}
        >
          <For each={rows().map((row) => row.id)} fallback={<p class="py-4 text-sm text-muted">{t("transactions_empty")}</p>}>
            {(id) => (
              <Show when={byId(id)}>
                {(row) => {
                  const selected = () => selection().ids.includes(id);
                  return (
                    <Highlight key={`tx:${id}`} class="rounded-control">
                      <div
                        role="option"
                        tabIndex={row().categoryDeleted ? -1 : 0}
                        aria-selected={selected()}
                        aria-disabled={row().categoryDeleted}
                        onClick={(event) => activate(row(), event)}
                        onKeyDown={(event) => {
                          if (event.key === "Enter" || event.key === " ") {
                            event.preventDefault();
                            activate(row(), event);
                          }
                        }}
                        onPointerDown={() => coarse() && !row().categoryDeleted && startPress(row())}
                        onPointerUp={endPress}
                        onPointerLeave={endPress}
                        onPointerCancel={endPress}
                        class="cursor-pointer select-none"
                        classList={{
                          "-mx-2.5 rounded-control border-b border-hairline px-2.5": !narrow(),
                          "rounded-[14px] border-[1.5px] px-3.5 py-2": narrow(),
                          "bg-selected": selected(),
                          "border-accent": narrow() && selected(),
                          "border-card-border bg-card": narrow() && !selected(),
                        }}
                      >
                        <TransactionRow
                          transaction={row()}
                          member={member(row().memberId)}
                          currencySign={household.data?.currencySign ?? ""}
                          today={today()}
                          {...(coarse() && selected() ? { badge: <span class="grid h-[30px] w-[30px] place-items-center rounded-full bg-accent text-xs text-white">✓</span> } : {})}
                        />
                      </div>
                    </Highlight>
                  );
                }}
              </Show>
            )}
          </For>
        </div>
        <Show when={pages.hasNextPage}>
          <Button onClick={() => void pages.fetchNextPage()}>{t("action_show_more")}</Button>
        </Show>
      </Show>
      <Show when={!coarse()}>
        <div class="flex items-center gap-2.5">
          <Button kind="primary" disabled={onlySelected() === undefined} onClick={() => setEditing(onlySelected() ?? null)}>
            {t("action_edit_selected")}
          </Button>
          <Button kind="danger" disabled={selectedCount() === 0} onClick={() => askRemove([...selection().ids])}>
            {t("action_remove_selected")}
          </Button>
          <span class="text-xs text-muted">
            {selectedCount() > 0 ? t("selected_count", { n: selectedCount() }) : t("selection_hint")}
          </span>
        </div>
      </Show>
      <Show when={editing()}>
        {(row) => <EditForm transaction={row()} budgets={budgets.data?.items ?? []} save={(changes) => save(row().id, changes)} cancel={() => setEditing(null)} />}
      </Show>
      <Show when={menu()}>
        {(open) => {
          const several = () => open().ids.length > 1;
          return (
            <Dialog open title={open().title} onClose={() => setMenu(null)}>
              <div class="flex flex-col gap-2">
                <b class="pb-1 text-center text-[15px]">{open().title}</b>
                <Button
                  disabled={several()}
                  onClick={() => {
                    const row = byId(open().ids[0] ?? "");
                    setMenu(null);
                    if (row !== undefined) setEditing(row);
                  }}
                >
                  {t("action_edit")}
                </Button>
                <Button kind="danger" onClick={() => askRemove(open().ids)}>
                  {several() ? t("remove_n", { n: open().ids.length }) : t("action_remove")}
                </Button>
                <Button kind="quiet" onClick={() => setMenu(null)}>
                  {t("action_cancel")}
                </Button>
              </div>
            </Dialog>
          );
        }}
      </Show>
      <Show when={confirming()}>
        {(ids) => (
          <ConfirmDialog
            title={t("remove_n_title", { n: ids().length })}
            body={t("remove_n_body")}
            confirmLabel={t("action_remove")}
            onClose={() => setConfirming(null)}
            onConfirm={() => remove(ids())}
          />
        )}
      </Show>
    </div>
  );
}
