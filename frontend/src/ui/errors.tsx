/**
 * Mutation failures as a dismissible notice (FRONTEND.md § 8.1). Field errors
 * are handled by the forms themselves; everything else lands here.
 */
import { useQueryClient } from "@tanstack/solid-query";
import { createSignal, Show } from "solid-js";

import type { TranslationKey } from "@/l10n";
import { ApiError } from "@/ports/api";
import { Notice } from "@/ui/components/basics";
import { useServices } from "@/ui/services";

const MESSAGE: Record<string, TranslationKey> = {
  GONE: "error_gone",
  READ_ONLY_HISTORY: "error_read_only",
  CATEGORY_DELETED: "error_read_only",
};

export function useNotice() {
  const { t } = useServices();
  const client = useQueryClient();
  const [message, setMessage] = createSignal<string | null>(null);

  /** Show *error* to the reader and refresh, since the data moved under them. */
  const report = (error: unknown) => {
    const code = error instanceof ApiError ? error.code : "";
    setMessage(t(MESSAGE[code] ?? "error_generic"));
    void client.invalidateQueries();
  };

  const view = () => (
    <Show when={message()}>
      {(text) => <Notice onDismiss={() => setMessage(null)}>{text()}</Notice>}
    </Show>
  );
  return { report, view };
}

/** After a successful write, refresh every screen's data. */
export function useRefresh() {
  const client = useQueryClient();
  return () => client.invalidateQueries();
}
