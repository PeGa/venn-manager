/** Forced password change (FRONTEND.md § 3.2, BACKEND.md § 8.4). */
import { useQueryClient } from "@tanstack/solid-query";
import { createSignal } from "solid-js";

import { keys } from "@/adapters/queries";
import { passwordProblem } from "@/domain/passwords";
import { ApiError } from "@/ports/api";
import { AuthCard } from "@/ui/auth/SignIn";
import { Button, Field } from "@/ui/components/basics";
import { useServices } from "@/ui/services";

export function PasswordForm(props: { onDone: () => void; submitLabel: string }) {
  const { api, t } = useServices();
  const [current, setCurrent] = createSignal("");
  const [next, setNext] = createSignal("");
  const [repeat, setRepeat] = createSignal("");
  const [errors, setErrors] = createSignal<{ current?: string; next?: string; repeat?: string }>({});
  const [busy, setBusy] = createSignal(false);

  const submit = async (event: SubmitEvent) => {
    event.preventDefault();
    const problem = passwordProblem(next(), repeat());
    if (problem === "length") return setErrors({ next: t("error_password_length") });
    if (problem === "mismatch") return setErrors({ repeat: t("error_password_mismatch") });
    setBusy(true);
    setErrors({});
    try {
      await api.changePassword(current(), next());
      setCurrent("");
      setNext("");
      setRepeat("");
      props.onDone();
    } catch (caught) {
      const wrong = caught instanceof ApiError && caught.field === "currentPassword";
      setErrors(wrong ? { current: t("error_current_password") } : { next: t("error_generic") });
    } finally {
      setBusy(false);
    }
  };

  return (
    <form class="flex flex-col gap-4" onSubmit={(event) => void submit(event)}>
      <Field label={t("field_current_password")} type="password" autocomplete="current-password" value={current()} onInput={(e) => setCurrent(e.currentTarget.value)} error={errors().current} required />
      <Field label={t("field_new_password")} type="password" autocomplete="new-password" value={next()} onInput={(e) => setNext(e.currentTarget.value)} error={errors().next} required />
      <Field label={t("field_repeat_password")} type="password" autocomplete="new-password" value={repeat()} onInput={(e) => setRepeat(e.currentTarget.value)} error={errors().repeat} required />
      <Button kind="primary" type="submit" disabled={busy()}>
        {props.submitLabel}
      </Button>
    </form>
  );
}

export function ForceChange() {
  const { api, t } = useServices();
  const client = useQueryClient();
  const logOut = async () => {
    await api.logout().catch(() => undefined);
    await client.resetQueries();
  };
  return (
    <AuthCard title={t("force_title")}>
      <p class="-mt-2 text-sm text-muted">{t("force_body")}</p>
      <PasswordForm submitLabel={t("action_change_password")} onDone={() => void client.invalidateQueries({ queryKey: keys.session })} />
      <Button kind="quiet" onClick={() => void logOut()}>
        {t("action_log_out")}
      </Button>
    </AuthCard>
  );
}
