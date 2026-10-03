/** Profile (FRONTEND.md § 5.8): the signed-in member's own account and preferences. */
import { useQuery, useQueryClient } from "@tanstack/solid-query";
import { createSignal, For, Show } from "solid-js";

import { keys } from "@/adapters/queries";
import type { Session, Theme } from "@/domain/model";
import { LANGUAGES, type Language } from "@/l10n";
import { ApiError, type ProfileChanges } from "@/ports/api";
import { PasswordForm } from "@/ui/auth/ForceChange";
import { Button, Chip, Field, Skeleton } from "@/ui/components/basics";
import { useNotice } from "@/ui/errors";
import { useServices } from "@/ui/services";

const LANGUAGE_NAME: Record<Language, string> = { en: "English", es: "Español" };
const THEMES: readonly Theme[] = ["light", "dark", "system"];

function Panel(props: { title: string; children: import("solid-js").JSX.Element }) {
  return (
    <section aria-label={props.title} class="rounded-[20px] border border-card-border bg-card p-5">
      <h2 class="mb-3 font-bold">{props.title}</h2>
      {props.children}
    </section>
  );
}

export function Profile() {
  const { api, t, language, narrow } = useServices();
  const client = useQueryClient();
  const session = useQuery(() => ({ queryKey: keys.session, queryFn: () => api.session() }));
  const notice = useNotice();
  const [name, setName] = createSignal<string | null>(null);
  const [username, setUsername] = createSignal<string | null>(null);
  const [usernameError, setUsernameError] = createSignal<string | undefined>();
  const [passwordDone, setPasswordDone] = createSignal(false);

  const update = async (changes: ProfileChanges): Promise<boolean> => {
    try {
      const fresh: Session = await api.updateMe(changes);
      client.setQueryData(keys.session, fresh);
      await client.invalidateQueries({ queryKey: keys.household });
      return true;
    } catch (caught) {
      if (caught instanceof ApiError && caught.code === "DUPLICATE_NAME") setUsernameError(t("error_username_taken"));
      else notice.report(caught);
      return false;
    }
  };
  const commitName = (current: string) => {
    const value = name()?.trim();
    setName(null);
    if (value && value !== current) void update({ realName: value });
  };
  const commitUsername = async (current: string) => {
    const value = username()?.trim();
    if (!value || value === current) {
      setUsername(null);
      return;
    }
    if (await update({ username: value })) {
      setUsername(null);
      setUsernameError(undefined);
    }
  };
  const signOut = async () => {
    await api.logout().catch(() => undefined);
    await client.resetQueries();
  };

  return (
    <Show when={session.data} fallback={<Skeleton lines={4} />}>
      {(data) => (
        <div class="flex flex-col gap-4">
          {notice.view()}
          <div class="grid items-start gap-4" classList={{ "grid-cols-3": !narrow(), "grid-cols-1 gap-2.5": narrow() }}>
            <Panel title={t("profile_account")}>
              <div class="flex flex-col gap-3.5">
                <Field
                  label={t("field_real_name")}
                  maxLength={128}
                  value={name() ?? data().member.realName}
                  onInput={(event) => setName(event.currentTarget.value)}
                  onBlur={() => commitName(data().member.realName)}
                  onKeyDown={(event) => event.key === "Enter" && commitName(data().member.realName)}
                />
                <Field
                  label={t("field_username")}
                  maxLength={64}
                  autocomplete="username"
                  value={username() ?? data().member.username}
                  error={usernameError()}
                  onInput={(event) => setUsername(event.currentTarget.value)}
                  onBlur={() => void commitUsername(data().member.username)}
                  onKeyDown={(event) => event.key === "Enter" && void commitUsername(data().member.username)}
                />
              </div>
            </Panel>
            <Panel title={t("profile_password")}>
              <PasswordForm submitLabel={t("action_change_password")} onDone={() => setPasswordDone(true)} />
              <Show when={passwordDone()}>
                <p role="status" class="mt-3 text-sm text-accent">
                  {t("password_changed")}
                </p>
              </Show>
            </Panel>
            <Panel title={t("profile_preferences")}>
              <p class="mb-1.5 text-xs font-semibold text-muted">{t("field_language")}</p>
              <div class="flex gap-1.5">
                <For each={LANGUAGES}>
                  {(code) => (
                    <Chip active={language() === code} onClick={() => void update({ language: code })}>
                      {LANGUAGE_NAME[code]}
                    </Chip>
                  )}
                </For>
              </div>
              <p class="mb-1.5 mt-4 text-xs font-semibold text-muted">{t("field_theme")}</p>
              <div class="flex gap-1.5">
                <For each={THEMES}>
                  {(theme) => (
                    <Chip active={data().preferences.theme === theme} onClick={() => void update({ theme })}>
                      {t(`theme_${theme}`)}
                    </Chip>
                  )}
                </For>
              </div>
            </Panel>
          </div>
          <div>
            <Button kind="danger" onClick={() => void signOut()}>
              {t("action_sign_out")}
            </Button>
          </div>
        </div>
      )}
    </Show>
  );
}
