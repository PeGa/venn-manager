/**
 * Sign-in and forced-password-change screens (FRONTEND.md § General description,
 * API_SURFACE.md § Force Password Change).
 *
 * The app has no self-registration: the first login uses the seeded admin
 * credentials, and that session may only call `POST /auth/password` until the
 * password is replaced.
 */
import { useState } from "preact/hooks";

import { ErrorNotice } from "./ErrorNotice";
import { Field } from "./Field";
import { useTranslation } from "@/hooks/useTranslation";
import { useChangePassword, useLogin, useLogout } from "@/hooks/useSession";
import {
  validatePassword,
  validatePasswordMatch,
  validateRequired,
  type Verdict,
} from "@/utils/validation";

export function LoginScreen() {
  const t = useTranslation();
  const login = useLogin();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState<{ username: Verdict; password: Verdict }>({
    username: null,
    password: null,
  });

  const submit = (): void => {
    const next = {
      username: validateRequired(username),
      password: validateRequired(password),
    };
    setErrors(next);
    if (next.username !== null || next.password !== null) {
      return;
    }
    login.mutate({ username: username.trim(), password });
  };

  return (
    <main class="mx-auto flex min-h-screen w-full max-w-sm flex-col justify-center p-4">
      <h1 class="mb-1 text-2xl font-semibold">{t("app_name")}</h1>
      <p class="mb-6 text-sm text-muted">{t("login_title")}</p>

      {login.error === null ? null : <ErrorNotice error={login.error} />}

      <form
        onSubmit={(event) => {
          event.preventDefault();
          submit();
        }}
      >
        <Field
          label={t("username_label")}
          value={username}
          error={errors.username}
          autoComplete="username"
          required
          onInput={setUsername}
        />
        <Field
          label={t("password_label")}
          type="password"
          value={password}
          error={errors.password}
          autoComplete="current-password"
          required
          onInput={setPassword}
        />
        <button
          type="submit"
          class="vm-button-primary w-full"
          disabled={login.isPending}
          data-testid="sign-in"
        >
          {login.isPending ? t("loading") : t("sign_in")}
        </button>
      </form>
    </main>
  );
}

export function ForcePasswordScreen() {
  const t = useTranslation();
  const changePassword = useChangePassword();
  const logout = useLogout();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [repeat, setRepeat] = useState("");
  const [errors, setErrors] = useState<{
    current: Verdict;
    next: Verdict;
    repeat: Verdict;
  }>({ current: null, next: null, repeat: null });

  const submit = (): void => {
    const checked = {
      current: validateRequired(current),
      next: validatePassword(next),
      repeat: validatePasswordMatch(next, repeat),
    };
    setErrors(checked);
    if (checked.current !== null || checked.next !== null || checked.repeat !== null) {
      return;
    }
    changePassword.mutate({ currentPassword: current, newPassword: next });
  };

  return (
    <main class="mx-auto flex min-h-screen w-full max-w-sm flex-col justify-center p-4">
      <h1 class="mb-1 text-xl font-semibold">{t("force_change_title")}</h1>
      <p class="mb-6 text-sm text-muted">{t("force_change_body")}</p>

      {changePassword.error === null ? null : <ErrorNotice error={changePassword.error} />}

      <form
        onSubmit={(event) => {
          event.preventDefault();
          submit();
        }}
      >
        <Field
          label={t("current_password_label")}
          type="password"
          value={current}
          error={errors.current}
          autoComplete="current-password"
          required
          onInput={setCurrent}
        />
        <Field
          label={t("new_password_label")}
          type="password"
          value={next}
          error={errors.next}
          autoComplete="new-password"
          required
          onInput={setNext}
        />
        <Field
          label={t("repeat_password_label")}
          type="password"
          value={repeat}
          error={errors.repeat}
          autoComplete="new-password"
          required
          onInput={setRepeat}
        />
        <button
          type="submit"
          class="vm-button-primary w-full"
          disabled={changePassword.isPending}
          data-testid="force-change-submit"
        >
          {changePassword.isPending ? t("loading") : t("change_password")}
        </button>
      </form>

      {/*
        API_SURFACE.md exempts POST /auth/logout from the force-change gate, so a
        restricted session can still hand the machine to someone else. Without
        this the exemption would be unreachable from the UI.
      */}
      <button
        type="button"
        class="vm-button mt-3 w-full"
        onClick={() => logout.mutate()}
        disabled={logout.isPending}
        data-testid="force-change-logout"
      >
        {t("logout")}
      </button>
    </main>
  );
}
