/** Budget concepts: add, rename inline, remove (FRONTEND.md § 5.7). */
import { createSignal, For, Show } from "solid-js";

import type { Budget } from "@/domain/model";
import { ApiError } from "@/ports/api";
import { Button } from "@/ui/components/basics";
import { ConfirmDialog } from "@/ui/components/ConfirmDialog";
import { SettingsCard } from "@/ui/screens/settings/SettingsCard";
import { useServices } from "@/ui/services";

export const BUDGET_NAME_MAX = 60;

export function ConceptsCard(props: {
  budgets: Budget[];
  add: (name: string) => Promise<void>;
  rename: (budget: Budget, name: string) => void;
  remove: (budget: Budget) => void;
}) {
  const { t } = useServices();
  const [draft, setDraft] = createSignal("");
  const [error, setError] = createSignal<string | null>(null);
  const [renaming, setRenaming] = createSignal<string | null>(null);
  const [removing, setRemoving] = createSignal<Budget | null>(null);

  const taken = (name: string, except?: string) =>
    props.budgets.some((budget) => budget.id !== except && budget.name.toLowerCase() === name.toLowerCase());

  const add = async (event: SubmitEvent) => {
    event.preventDefault();
    const name = draft().trim();
    if (name === "") return;
    if (taken(name)) {
      setError(t("error_name_taken"));
      return;
    }
    try {
      await props.add(name);
      setDraft("");
      setError(null);
    } catch (caught) {
      const duplicate = caught instanceof ApiError && caught.code === "DUPLICATE_NAME";
      setError(t(duplicate ? "error_name_taken" : "error_generic"));
    }
  };

  const finishRename = (budget: Budget, value: string) => {
    setRenaming(null);
    const name = value.trim();
    if (name !== "" && name !== budget.name && !taken(name, budget.id)) props.rename(budget, name);
  };

  return (
    <SettingsCard section="budgets" title={t("concepts_title")} subtitle={t("concepts_subtitle")}>
      <ul>
        <For each={props.budgets}>
          {(budget) => (
            <li class="flex items-center border-t border-hairline py-2 text-sm">
              <Show
                when={renaming() === budget.id}
                fallback={
                  <button
                    type="button"
                    aria-label={t("concept_rename", { name: budget.name })}
                    class="flex-1 text-left"
                    onClick={() => setRenaming(budget.id)}
                  >
                    {budget.name}
                  </button>
                }
              >
                <input
                  aria-label={t("concept_name_of", { name: budget.name })}
                  value={budget.name}
                  maxLength={BUDGET_NAME_MAX}
                  ref={(element) => queueMicrotask(() => element.focus())}
                  onKeyDown={(event) => {
                    if (event.key === "Enter") finishRename(budget, event.currentTarget.value);
                    if (event.key === "Escape") setRenaming(null);
                  }}
                  onBlur={(event) => finishRename(budget, event.currentTarget.value)}
                  class="min-w-0 flex-1 rounded-lg border border-input-border bg-input-bg px-2 py-1 text-sm"
                />
              </Show>
              <button
                type="button"
                aria-label={t("concept_remove", { name: budget.name })}
                class="px-1 text-lg leading-none text-coral-text"
                onClick={() => setRemoving(budget)}
              >
                ×
              </button>
            </li>
          )}
        </For>
      </ul>
      <form class="mt-2.5 flex gap-2" onSubmit={(event) => void add(event)}>
        <input
          aria-label={t("concept_new")}
          placeholder={t("concept_placeholder")}
          maxLength={BUDGET_NAME_MAX}
          value={draft()}
          onInput={(event) => {
            setDraft(event.currentTarget.value);
            setError(null);
          }}
          class="min-w-0 flex-1 rounded-control border border-input-border bg-input-bg px-3 py-2 text-[13px]"
        />
        <Button kind="primary" type="submit" small>
          {t("action_add")}
        </Button>
      </form>
      <Show when={error()}>
        <p class="mt-1.5 text-xs text-coral-text">{error()}</p>
      </Show>
      <Show when={removing()}>
        {(budget) => (
          <ConfirmDialog
            title={t("concept_remove_title", { name: budget().name })}
            body={t("concept_remove_body")}
            confirmLabel={t("action_remove")}
            onClose={() => setRemoving(null)}
            onConfirm={() => {
              props.remove(budget());
              setRemoving(null);
            }}
          />
        )}
      </Show>
    </SettingsCard>
  );
}
