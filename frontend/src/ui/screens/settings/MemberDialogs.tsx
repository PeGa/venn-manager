/** Admin-only member dialogs: invite and account (FRONTEND.md § 5.7). */
import { createSignal } from "solid-js";

import type { Member } from "@/domain/model";
import { PASSWORD_MAX, PASSWORD_MIN } from "@/domain/passwords";
import { ApiError, type MemberChanges } from "@/ports/api";
import { Button, Field } from "@/ui/components/basics";
import { Dialog } from "@/ui/components/Dialog";
import { useRefresh } from "@/ui/errors";
import { useServices } from "@/ui/services";

function passwordOk(password: string): boolean {
  return password.length >= PASSWORD_MIN && password.length <= PASSWORD_MAX;
}

function AdminToggle(props: { checked: boolean; onChange: (checked: boolean) => void }) {
  const { t } = useServices();
  return (
    <label class="flex items-center gap-2 text-sm font-semibold">
      <input
        type="checkbox"
        checked={props.checked}
        onChange={(event) => props.onChange(event.currentTarget.checked)}
        class="h-4 w-4 accent-[var(--accent)]"
      />
      {t("role_admin")}
    </label>
  );
}

export function InviteDialog(props: { name: string; onClose: () => void }) {
  const { api, t } = useServices();
  const refresh = useRefresh();
  // eslint-disable-next-line solid/reactivity -- prefilled once, then edited here.
  const [realName, setRealName] = createSignal(props.name);
  const [username, setUsername] = createSignal("");
  const [password, setPassword] = createSignal("");
  const [admin, setAdmin] = createSignal(false);
  const [errors, setErrors] = createSignal<{ username?: string; password?: string; form?: string }>({});

  const submit = async (event: SubmitEvent) => {
    event.preventDefault();
    if (!passwordOk(password())) {
      setErrors({ password: t("error_password_length") });
      return;
    }
    try {
      await api.createMember({
        username: username().trim(),
        realName: realName().trim(),
        password: password(),
        isAdmin: admin(),
      });
      await refresh();
      props.onClose();
    } catch (caught) {
      const taken = caught instanceof ApiError && caught.code === "DUPLICATE_NAME";
      setErrors(taken ? { username: t("error_username_taken") } : { form: t("error_generic") });
    }
  };

  return (
    <Dialog open title={t("invite_title")} onClose={() => props.onClose()}>
      <h2 class="text-[17px] font-bold">{t("invite_title")}</h2>
      <form class="mt-4 flex flex-col gap-3.5" onSubmit={(event) => void submit(event)}>
        <Field
          label={t("field_real_name")}
          value={realName()}
          onInput={(event) => setRealName(event.currentTarget.value)}
          required
          maxLength={128}
        />
        <Field
          label={t("field_username")}
          value={username()}
          onInput={(event) => setUsername(event.currentTarget.value)}
          error={errors().username}
          required
          maxLength={64}
        />
        <Field
          label={t("field_initial_password")}
          type="password"
          autocomplete="new-password"
          value={password()}
          onInput={(event) => setPassword(event.currentTarget.value)}
          error={errors().password}
          required
        />
        <AdminToggle checked={admin()} onChange={setAdmin} />
        <p class="text-xs text-muted">{t("invite_hint")}</p>
        <p class="text-xs text-coral-text">{errors().form}</p>
        <div class="flex justify-end gap-2.5">
          <Button onClick={() => props.onClose()}>{t("action_cancel")}</Button>
          <Button kind="primary" type="submit">
            {t("action_invite")}
          </Button>
        </div>
      </form>
    </Dialog>
  );
}

function memberChanges(member: Member, realName: string, admin: boolean, password: string): MemberChanges {
  const changes: MemberChanges = {};
  if (realName !== member.realName) changes.realName = realName;
  if (admin !== (member.role === "admin")) changes.isAdmin = admin;
  if (password !== "") changes.password = password;
  return changes;
}

export function AccountDialog(props: { member: Member; onClose: () => void }) {
  const { api, t } = useServices();
  const refresh = useRefresh();
  // eslint-disable-next-line solid/reactivity -- the dialog edits a copy taken when it opens.
  const [realName, setRealName] = createSignal(props.member.realName);
  // eslint-disable-next-line solid/reactivity
  const [admin, setAdmin] = createSignal(props.member.role === "admin");
  const [password, setPassword] = createSignal("");
  const [error, setError] = createSignal<string | undefined>();

  const submit = async (event: SubmitEvent) => {
    event.preventDefault();
    if (password() !== "" && !passwordOk(password())) {
      setError(t("error_password_length"));
      return;
    }
    const changes = memberChanges(props.member, realName().trim(), admin(), password());
    if (Object.keys(changes).length === 0) {
      props.onClose();
      return;
    }
    try {
      await api.updateMember(props.member.id, changes);
      await refresh();
      props.onClose();
    } catch (caught) {
      const last = caught instanceof ApiError && caught.code === "LAST_ADMIN";
      setError(t(last ? "error_last_admin" : "error_generic"));
    }
  };

  const title = () => t("account_title", { name: props.member.realName });
  return (
    <Dialog open title={title()} onClose={() => props.onClose()}>
      <h2 class="text-[17px] font-bold">{title()}</h2>
      <form class="mt-4 flex flex-col gap-3.5" onSubmit={(event) => void submit(event)}>
        <Field
          label={t("field_real_name")}
          value={realName()}
          onInput={(event) => setRealName(event.currentTarget.value)}
          required
          maxLength={128}
        />
        <AdminToggle checked={admin()} onChange={setAdmin} />
        <Field
          label={t("field_new_password_optional")}
          type="password"
          autocomplete="new-password"
          value={password()}
          onInput={(event) => setPassword(event.currentTarget.value)}
        />
        <p class="text-xs text-coral-text">{error()}</p>
        <div class="flex justify-end gap-2.5">
          <Button onClick={() => props.onClose()}>{t("action_cancel")}</Button>
          <Button kind="primary" type="submit">
            {t("action_save")}
          </Button>
        </div>
      </form>
    </Dialog>
  );
}
