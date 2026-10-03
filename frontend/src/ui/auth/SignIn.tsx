/** Sign in (FRONTEND.md § 3.1). Shown in the browser's language. */
import { useQueryClient } from "@tanstack/solid-query";
import { createSignal, Show } from "solid-js";

import { keys } from "@/adapters/queries";
import { ApiError } from "@/ports/api";
import { Button, Field } from "@/ui/components/basics";
import { useServices } from "@/ui/services";

export function AuthCard(props: { title: string; children: import("solid-js").JSX.Element }) {
  const { t } = useServices();
  return (
    <main class="grid min-h-dvh place-items-center bg-ground px-4 py-10 text-ink">
      <section class="flex w-full max-w-sm flex-col gap-5 rounded-card border border-card-border bg-card p-7 shadow-frame">
        <div>
          <p class="text-sm font-bold text-accent">{t("app_name")}</p>
          <h1 class="mt-1 text-[22px] font-bold">{props.title}</h1>
        </div>
        {props.children}
      </section>
    </main>
  );
}

export function SignIn() {
  const { api, t } = useServices();
  const client = useQueryClient();
  const [username, setUsername] = createSignal("");
  const [password, setPassword] = createSignal("");
  const [error, setError] = createSignal<string | null>(null);
  const [busy, setBusy] = createSignal(false);

  const submit = async (event: SubmitEvent) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      client.setQueryData(keys.session, await api.login(username().trim(), password()));
    } catch (caught) {
      const invalid = caught instanceof ApiError && caught.code === "UNAUTHORIZED";
      setError(t(invalid ? "error_invalid_credentials" : "error_generic"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthCard title={t("sign_in_title")}>
      <form class="flex flex-col gap-4" onSubmit={(event) => void submit(event)}>
        <Field label={t("field_username")} autocomplete="username" value={username()} onInput={(e) => setUsername(e.currentTarget.value)} required />
        <Field
          label={t("field_password")}
          type="password"
          autocomplete="current-password"
          value={password()}
          onInput={(e) => setPassword(e.currentTarget.value)}
          required
        />
        <Show when={error()}>
          <p role="alert" class="text-sm text-coral-text">
            {error()}
          </p>
        </Show>
        <Button kind="primary" type="submit" disabled={busy()}>
          {t("action_sign_in")}
        </Button>
      </form>
    </AuthCard>
  );
}
