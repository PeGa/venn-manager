/**
 * Month switch state (FRONTEND.md § 2, BACKEND.md § 3).
 *
 * The month state is polled, not pushed: AGENTS.md forbids WebSocket and SSE.
 * When the server reports a new month the dialog is offered once; if the user
 * declines, Home and Budget show a "Switch to current month" button instead.
 *
 * Held in context so the decline survives navigation between those two screens
 * without a state library — AGENTS.md allows context and forbids Redux & co.
 */
import type { ComponentChildren } from "preact";
import { createContext } from "preact";
import { useContext, useMemo, useState } from "preact/hooks";

import { ConfirmDialog } from "./ConfirmDialog";
import { useMonthState, useSwitchMonth } from "@/hooks/useProjections";
import { useTranslation } from "@/hooks/useTranslation";
import type { MonthState } from "@/types/api";

export interface MonthSwitchValue {
  state: MonthState | undefined;
  loading: boolean;
  error: unknown;
  /** The user's working month, which Home and Budget operate on. */
  workingMonth: string | undefined;
  dialogVisible: boolean;
  declined: boolean;
  switching: boolean;
  decline: () => void;
  confirm: () => void;
  refetch: () => void;
}

const MonthSwitchContext = createContext<MonthSwitchValue | null>(null);

export function MonthSwitchProvider({
  enabled,
  children,
}: {
  enabled: boolean;
  children: ComponentChildren;
}) {
  const query = useMonthState(enabled);
  const mutation = useSwitchMonth();
  const [declined, setDeclined] = useState(false);
  const state = query.data?.data;

  const value = useMemo<MonthSwitchValue>(
    () => ({
      state,
      loading: query.isLoading,
      error: query.error,
      workingMonth: state?.last_acknowledged_month,
      dialogVisible: state?.needs_switch === true && !declined,
      declined,
      switching: mutation.isPending,
      decline: () => setDeclined(true),
      confirm: () => {
        mutation.mutate();
        setDeclined(false);
      },
      refetch: () => {
        void query.refetch();
      },
    }),
    [state, query.isLoading, query.error, query, mutation, declined],
  );

  return (
    <MonthSwitchContext.Provider value={value}>{children}</MonthSwitchContext.Provider>
  );
}

/** Read the month-switch state. Throws outside a provider, which is a bug. */
export function useMonthSwitch(): MonthSwitchValue {
  const value = useContext(MonthSwitchContext);
  if (value === null) {
    throw new Error("useMonthSwitch must be used inside MonthSwitchProvider");
  }
  return value;
}

/** The dialog offered when the calendar has moved past the working month. */
export function MonthSwitchDialog() {
  const t = useTranslation();
  const monthSwitch = useMonthSwitch();
  const state = monthSwitch.state;
  if (!monthSwitch.dialogVisible || state === undefined) {
    return null;
  }
  return (
    <ConfirmDialog
      title={t("month_switch_title")}
      body={t("month_switch_body", { current: state.current_month })}
      confirmLabel={t("month_switch_confirm", { current: state.current_month })}
      cancelLabel={t("month_switch_decline", {
        working: state.last_acknowledged_month,
      })}
      busy={monthSwitch.switching}
      onConfirm={monthSwitch.confirm}
      onCancel={monthSwitch.decline}
    />
  );
}

/** The button shown on Home and Budget after the dialog is declined. */
export function SwitchCta() {
  const t = useTranslation();
  const monthSwitch = useMonthSwitch();
  if (monthSwitch.state?.needs_switch !== true || !monthSwitch.declined) {
    return null;
  }
  return (
    <button
      type="button"
      class="vm-button-primary"
      onClick={monthSwitch.confirm}
      disabled={monthSwitch.switching}
      data-testid="switch-cta"
    >
      {monthSwitch.switching ? t("loading") : t("switch_cta")}
    </button>
  );
}
