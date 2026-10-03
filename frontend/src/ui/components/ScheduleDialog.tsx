/** When a budget is due (FRONTEND.md § 4.3). */
import { createSignal, Show, For } from "solid-js";

import type { Repeat, Schedule } from "@/domain/model";
import { Button } from "@/ui/components/basics";
import { Dialog } from "@/ui/components/Dialog";
import { useServices } from "@/ui/services";

const REPEATS: readonly (Repeat | "none")[] = ["none", "once", "weekly", "biweekly", "monthly"];

export function ScheduleDialog(props: {
  open: boolean;
  name: string;
  schedule: Schedule | null;
  onSave: (schedule: Schedule | null) => void;
  onClose: () => void;
}) {
  const { t } = useServices();
  // eslint-disable-next-line solid/reactivity -- the dialog edits a copy taken when it opens.
  const [repeat, setRepeat] = createSignal<Repeat | "none">(props.schedule?.repeat ?? "none");
  // eslint-disable-next-line solid/reactivity
  const [anchor, setAnchor] = createSignal(props.schedule?.anchor ?? "");
  const [missingDate, setMissingDate] = createSignal(false);
  const label = (value: Repeat | "none") => t(`repeat_${value}`);

  const save = () => {
    const kind = repeat();
    if (kind === "none") {
      props.onSave(null);
    } else if (anchor() === "") {
      setMissingDate(true);
    } else {
      props.onSave({ repeat: kind, anchor: anchor() });
    }
  };

  return (
    <Dialog open={props.open} title={t("schedule_title", { name: props.name })} onClose={() => {
        props.onClose();
      }}
    >
      <h2 class="text-[17px] font-bold">{t("schedule_title", { name: props.name })}</h2>
      <div class="mt-4 flex flex-col gap-4">
        <label class="flex flex-col gap-1 text-xs font-semibold text-muted">
          {t("field_repeat")}
          <select
            value={repeat()}
            onChange={(event) => setRepeat(event.currentTarget.value as Repeat | "none")}
            class="rounded-control border border-input-border bg-input-bg px-3 py-2.5 text-sm font-normal text-ink"
          >
            <For each={REPEATS}>{(value) => (
              <option value={value}>{label(value)}</option>
            )}</For>
          </select>
        </label>
        <Show when={repeat() !== "none"}>
          <label class="flex flex-col gap-1 text-xs font-semibold text-muted">
            {t(repeat() === "once" ? "field_due_date" : "field_first_due_date")}
            <input
              type="date"
              value={anchor()}
              onInput={(event) => {
                setAnchor(event.currentTarget.value);
                setMissingDate(false);
              }}
              aria-invalid={missingDate()}
              class="rounded-control border border-input-border bg-input-bg px-3 py-2.5 text-sm font-normal text-ink"
            />
          </label>
          <Show when={missingDate()}>
            <p class="-mt-2 text-xs text-coral-text">{t("error_pick_date")}</p>
          </Show>
        </Show>
      </div>
      <div class="mt-6 flex justify-end gap-2.5">
        <Button onClick={() => props.onClose()}>{t("action_cancel")}</Button>
        <Button kind="primary" onClick={save}>
          {t("action_save")}
        </Button>
      </div>
    </Dialog>
  );
}
