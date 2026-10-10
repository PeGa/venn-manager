/**
 * The category picker (FRONTEND.md § 4.6): a button that unfolds every budget
 * as wrapping chips, in creation order.
 *
 * The box is positioned under the nearest positioned ancestor, so the caller
 * decides how wide it is by marking its container `relative`.
 */
import { createSignal, For, onCleanup, onMount, Show } from "solid-js";

import type { Budget } from "@/domain/model";
import { Chip } from "@/ui/components/basics";
import { useServices } from "@/ui/services";

export function CategoryPicker(props: {
  budgets: Budget[];
  selected: string | null;
  onSelect: (budgetId: string) => void;
  /** Shown when the selected budget is not in the list, e.g. a transaction's deleted one. */
  fallbackName?: string;
  class?: string;
}) {
  const { t } = useServices();
  const [open, setOpen] = createSignal(false);
  let root: HTMLDivElement | undefined;

  const name = () => props.budgets.find((budget) => budget.id === props.selected)?.name ?? props.fallbackName ?? "";
  const onOutside = (event: PointerEvent) => {
    if (open() && root !== undefined && !root.contains(event.target as Node)) setOpen(false);
  };
  onMount(() => document.addEventListener("pointerdown", onOutside));
  onCleanup(() => document.removeEventListener("pointerdown", onOutside));

  const choose = (budgetId: string) => {
    props.onSelect(budgetId);
    setOpen(false);
  };

  return (
    <div
      ref={root}
      class={props.class}
      onKeyDown={(event) => {
        if (event.key === "Escape" && open()) {
          // Inside a dialog, Escape closes only the box.
          event.preventDefault();
          event.stopPropagation();
          setOpen(false);
        }
      }}
    >
      <button
        type="button"
        aria-label={t("category_button", { name: name() })}
        aria-haspopup="true"
        aria-expanded={open()}
        onClick={() => setOpen(!open())}
        class="flex w-full min-w-0 items-center gap-1.5 rounded-control border border-input-border bg-card px-3 py-2.5 text-[13px]"
      >
        <span class="min-w-0 flex-1 truncate text-left">{name()}</span>
        <span aria-hidden="true" class="text-muted" classList={{ "rotate-180": open() }}>
          ▾
        </span>
      </button>
      <Show when={open()}>
        <div
          role="group"
          aria-label={t("category_box")}
          class="absolute inset-x-0 top-full z-10 mt-1.5 flex flex-wrap gap-1.5 rounded-2xl border border-card-border bg-card p-3 shadow-modal"
        >
          <For each={props.budgets}>
            {(budget) => (
              <Chip active={budget.id === props.selected} onClick={() => choose(budget.id)}>
                {budget.name}
              </Chip>
            )}
          </For>
        </div>
      </Show>
    </div>
  );
}
