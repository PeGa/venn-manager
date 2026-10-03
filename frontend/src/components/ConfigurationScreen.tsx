/**
 * Configuration (FRONTEND.md § 5): Profile for everyone, Management for admins.
 *
 * Profile covers the caller's username, real name, password, language, currency
 * and theme. Currency is global, so changing it is gated by a dialog saying it
 * affects every user — the backend deliberately does not enforce that dialog.
 */
import { useState } from "preact/hooks";

import { ConfirmDialog } from "./ConfirmDialog";
import { DataTable, type Column } from "./DataTable";
import { ErrorNotice } from "./ErrorNotice";
import { Field, SelectField } from "./Field";
import { Modal } from "./Modal";
import { useTranslation } from "@/hooks/useTranslation";
import { useSettings, useUpdateSettings } from "@/hooks/useSettings";
import { useChangePassword } from "@/hooks/useSession";
import {
  useCreateUser,
  useDeleteUser,
  useUpdateUser,
  useUsers,
} from "@/hooks/useUsers";
import { languages } from "@/l10n";
import type { Language, Theme, UserSummary } from "@/types/api";
import {
  validateCurrency,
  validatePassword,
  validatePasswordMatch,
  validateRealName,
  validateRequired,
  validateUsername,
  type Verdict,
} from "@/utils/validation";

const THEMES: Theme[] = ["light", "dark", "system"];

export function ConfigurationScreen({ isAdmin }: { isAdmin: boolean }) {
  const t = useTranslation();
  return (
    <div class="space-y-6">
      <h2 class="text-lg font-semibold">{t("configuration_title")}</h2>
      <ProfileSection />
      {isAdmin ? <ManagementSection /> : null}
    </div>
  );
}

function ProfileSection() {
  const t = useTranslation();
  const settings = useSettings(true);
  const update = useUpdateSettings();
  const current = settings.data?.data;

  const [username, setUsername] = useState("");
  const [realName, setRealName] = useState("");
  const [currency, setCurrency] = useState("");
  const [currencyWarning, setCurrencyWarning] = useState(false);
  const [errors, setErrors] = useState<{
    username: Verdict;
    realName: Verdict;
    currency: Verdict;
  }>({ username: null, realName: null, currency: null });

  // The form mirrors the stored values until the user edits a field.
  const usernameValue = username === "" ? (current?.username ?? "") : username;
  const realNameValue = realName === "" ? (current?.real_name ?? "") : realName;
  const currencyValue = currency === "" ? (current?.currency ?? "") : currency;

  const saveProfile = (): void => {
    const checked = {
      username: validateUsername(usernameValue),
      realName: validateRealName(realNameValue),
    };
    setErrors((previous) => ({ ...previous, ...checked }));
    if (checked.username !== null || checked.realName !== null) {
      return;
    }
    update.mutate({ username: usernameValue.trim(), real_name: realNameValue.trim() });
  };

  const saveCurrency = (): void => {
    const checked = validateCurrency(currencyValue);
    setErrors((previous) => ({ ...previous, currency: checked }));
    if (checked !== null) {
      return;
    }
    setCurrencyWarning(true);
  };

  return (
    <section class="vm-card space-y-4">
      <h3 class="font-semibold">{t("profile_title")}</h3>
      {update.error === null ? null : <ErrorNotice error={update.error} />}

      <Field
        label={t("username_label")}
        value={usernameValue}
        error={errors.username}
        required
        onInput={setUsername}
      />
      <Field
        label={t("real_name_label")}
        value={realNameValue}
        error={errors.realName}
        required
        onInput={setRealName}
      />
      <button type="button" class="vm-button-primary" onClick={saveProfile} disabled={update.isPending}>
        {t("save")}
      </button>

      <hr class="border-border" />

      <SelectField
        label={t("language_label")}
        value={current?.language ?? "en"}
        onChange={(value) => update.mutate({ language: value as Language })}
        options={languages.map((language) => ({
          value: language,
          label: language === "en" ? "English" : "Español",
        }))}
      />
      <SelectField
        label={t("theme_label")}
        value={current?.theme ?? "system"}
        onChange={(value) => update.mutate({ theme: value as Theme })}
        options={THEMES.map((theme) => ({
          value: theme,
          label: t(theme === "light" ? "theme_light" : theme === "dark" ? "theme_dark" : "theme_system"),
        }))}
      />
      <Field
        label={t("currency_label")}
        value={currencyValue}
        error={errors.currency}
        required
        onInput={setCurrency}
      />
      <button type="button" class="vm-button" onClick={saveCurrency}>
        {t("save")}
      </button>

      <hr class="border-border" />
      <PasswordForm />

      {currencyWarning ? (
        <ConfirmDialog
          title={t("currency_warning_title")}
          body={t("currency_warning_body")}
          confirmLabel={t("confirm")}
          busy={update.isPending}
          onCancel={() => setCurrencyWarning(false)}
          onConfirm={() => {
            update.mutate(
              { currency: currencyValue },
              {
                onSuccess: () => {
                  setCurrency("");
                  setCurrencyWarning(false);
                },
              },
            );
          }}
        />
      ) : null}
    </section>
  );
}

/**
 * The caller's own password change.
 *
 * Presented inside Profile (FRONTEND.md § 5.1.1) but it calls `POST
 * /auth/password`, not the settings endpoint.
 */
function PasswordForm() {
  const t = useTranslation();
  const changePassword = useChangePassword();
  const [currentPassword, setCurrentPassword] = useState("");
  const [next, setNext] = useState("");
  const [repeat, setRepeat] = useState("");
  const [verdicts, setVerdicts] = useState<{
    current: Verdict;
    next: Verdict;
    repeat: Verdict;
  }>({ current: null, next: null, repeat: null });

  const submit = (): void => {
    const checked = {
      current: validateRequired(currentPassword),
      next: validatePassword(next),
      repeat: validatePasswordMatch(next, repeat),
    };
    setVerdicts(checked);
    if (checked.current !== null || checked.next !== null || checked.repeat !== null) {
      return;
    }
    changePassword.mutate(
      { currentPassword, newPassword: next },
      {
        onSuccess: () => {
          setCurrentPassword("");
          setNext("");
          setRepeat("");
        },
      },
    );
  };

  return (
    <div class="space-y-1">
      <h4 class="font-semibold">{t("change_password")}</h4>
      {changePassword.error === null ? null : (
        <ErrorNotice error={changePassword.error} />
      )}
      <Field
        label={t("current_password_label")}
        type="password"
        value={currentPassword}
        error={verdicts.current}
        autoComplete="current-password"
        onInput={setCurrentPassword}
      />
      <Field
        label={t("new_password_label")}
        type="password"
        value={next}
        error={verdicts.next}
        autoComplete="new-password"
        onInput={setNext}
      />
      <Field
        label={t("repeat_password_label")}
        type="password"
        value={repeat}
        error={verdicts.repeat}
        autoComplete="new-password"
        onInput={setRepeat}
      />
      <button
        type="button"
        class="vm-button-primary"
        onClick={submit}
        disabled={changePassword.isPending}
        data-testid="change-password"
      >
        {t("change_password")}
      </button>
    </div>
  );
}

function ManagementSection() {
  const t = useTranslation();
  const users = useUsers(true);
  const createUser = useCreateUser();
  const updateUser = useUpdateUser();
  const deleteUser = useDeleteUser();
  const [adding, setAdding] = useState(false);
  const [pendingDelete, setPendingDelete] = useState<UserSummary | null>(null);

  const columns: Array<Column<UserSummary>> = [
    { key: "username", header: t("username_label"), render: (user) => user.username },
    {
      key: "realName",
      header: t("real_name_label"),
      render: (user) => (
        <RealNameCell
          user={user}
          onSave={(realName) => updateUser.mutate({ id: user.id, patch: { real_name: realName } })}
        />
      ),
    },
    {
      key: "password",
      header: t("password_label"),
      render: (user) => <PasswordCell userId={user.id} />,
    },
    {
      key: "isAdmin",
      header: t("is_admin_column"),
      render: (user) => (
        <input
          type="checkbox"
          checked={user.is_admin}
          aria-label={`${t("is_admin_column")}: ${user.username}`}
          data-testid={`admin-${user.id}`}
          onChange={(event) =>
            updateUser.mutate({
              id: user.id,
              patch: { is_admin: event.currentTarget.checked },
            })
          }
        />
      ),
    },
    {
      key: "actions",
      header: t("delete"),
      render: (user) => (
        <button
          type="button"
          class="vm-button-danger"
          onClick={() => setPendingDelete(user)}
          data-testid={`delete-user-${user.id}`}
        >
          {t("delete")}
        </button>
      ),
    },
  ];

  return (
    <section class="vm-card space-y-4">
      <header class="flex items-center justify-between gap-3">
        <h3 class="font-semibold">{t("management_title")}</h3>
        <button
          type="button"
          class="vm-button-primary"
          onClick={() => setAdding(true)}
          data-testid="add-user"
        >
          {t("add_user")}
        </button>
      </header>

      {users.error === null ? null : <ErrorNotice error={users.error} />}
      {updateUser.error === null ? null : <ErrorNotice error={updateUser.error} />}
      {deleteUser.error === null ? null : <ErrorNotice error={deleteUser.error} />}

      <DataTable
        caption={t("users_grid_title")}
        columns={columns}
        rows={users.data?.data ?? []}
        rowId={(user) => user.id}
        rowLabel={(user) => user.username}
        emptyMessage={t("no_results")}
      />

      {adding ? (
        <AddUserDialog
          busy={createUser.isPending}
          error={createUser.error}
          onCancel={() => setAdding(false)}
          onCreate={(input) => {
            createUser.mutate(input, { onSuccess: () => setAdding(false) });
          }}
        />
      ) : null}

      {pendingDelete === null ? null : (
        <ConfirmDialog
          title={t("delete_user_warning_title")}
          body={t("delete_user_warning_body")}
          confirmLabel={t("delete")}
          destructive
          busy={deleteUser.isPending}
          onCancel={() => setPendingDelete(null)}
          onConfirm={() => {
            deleteUser.mutate(pendingDelete.id, {
              onSuccess: () => setPendingDelete(null),
            });
          }}
        />
      )}
    </section>
  );
}

/** Real name is editable in place, matching the grid in FRONTEND.md § 5.1.1.3. */
function RealNameCell({ user, onSave }: { user: UserSummary; onSave: (value: string) => void }) {
  const [value, setValue] = useState(user.real_name);
  const [verdict, setVerdict] = useState<Verdict>(null);
  const t = useTranslation();

  return (
    <span class="flex items-center gap-2">
      <input
        class="vm-input"
        value={value}
        aria-label={`${t("real_name_label")}: ${user.username}`}
        aria-invalid={verdict !== null}
        onInput={(event) => setValue(event.currentTarget.value)}
      />
      <button
        type="button"
        class="vm-button"
        data-testid={`save-real-name-${user.id}`}
        onClick={() => {
          const checked = validateRealName(value);
          setVerdict(checked);
          if (checked === null) {
            onSave(value.trim());
          }
        }}
      >
        {t("save")}
      </button>
      {verdict === null ? null : (
        <span class="vm-error" role="alert">
          {t(verdict)}
        </span>
      )}
    </span>
  );
}

/**
 * Password and repeat-password, in the grid, per FRONTEND.md § 5.1.1.3.1.
 *
 * Writing a password also ends that user's sessions on the server, which is the
 * point of an admin reset.
 */
function PasswordCell({ userId }: { userId: number }) {
  const t = useTranslation();
  const updateUser = useUpdateUser();
  const [password, setPassword] = useState("");
  const [repeat, setRepeat] = useState("");
  const [verdict, setVerdict] = useState<Verdict>(null);

  const save = (): void => {
    const checked = validatePassword(password) ?? validatePasswordMatch(password, repeat);
    setVerdict(checked);
    if (checked !== null) {
      return;
    }
    updateUser.mutate(
      { id: userId, patch: { password } },
      {
        onSuccess: () => {
          setPassword("");
          setRepeat("");
        },
      },
    );
  };

  return (
    <span class="flex items-center gap-2">
      <input
        class="vm-input"
        type="password"
        value={password}
        autoComplete="new-password"
        aria-label={`${t("password_label")}`}
        onInput={(event) => setPassword(event.currentTarget.value)}
      />
      <input
        class="vm-input"
        type="password"
        value={repeat}
        autoComplete="new-password"
        aria-label={`${t("repeat_password_label")}`}
        aria-invalid={verdict !== null}
        onInput={(event) => setRepeat(event.currentTarget.value)}
      />
      <button
        type="button"
        class="vm-button"
        data-testid={`save-password-${userId}`}
        onClick={save}
      >
        {t("save")}
      </button>
      {verdict === null ? null : (
        <span class="vm-error" role="alert">
          {t(verdict)}
        </span>
      )}
      {updateUser.error === null ? null : <ErrorNotice error={updateUser.error} />}
    </span>
  );
}

interface AddUserDialogProps {
  busy: boolean;
  error: unknown;
  onCancel: () => void;
  onCreate: (input: {
    username: string;
    real_name: string;
    password: string;
    is_admin: boolean;
  }) => void;
}

function AddUserDialog({ busy, error, onCancel, onCreate }: AddUserDialogProps) {
  const t = useTranslation();
  const [username, setUsername] = useState("");
  const [realName, setRealName] = useState("");
  const [password, setPassword] = useState("");
  const [repeat, setRepeat] = useState("");
  const [isAdmin, setIsAdmin] = useState(false);
  const [verdicts, setVerdicts] = useState<{
    username: Verdict;
    realName: Verdict;
    password: Verdict;
    repeat: Verdict;
  }>({ username: null, realName: null, password: null, repeat: null });

  const submit = (): void => {
    const checked = {
      username: validateUsername(username),
      realName: validateRealName(realName),
      password: validatePassword(password),
      repeat: validatePasswordMatch(password, repeat),
    };
    setVerdicts(checked);
    const failed = Object.values(checked).some((verdict) => verdict !== null);
    if (failed) {
      return;
    }
    onCreate({
      username: username.trim(),
      real_name: realName.trim(),
      password,
      is_admin: isAdmin,
    });
  };

  return (
    <Modal
      title={t("add_user")}
      onClose={onCancel}
      footer={
        <>
          <button type="button" class="vm-button" onClick={onCancel} disabled={busy}>
            {t("cancel")}
          </button>
          <button
            type="button"
            class="vm-button-primary"
            onClick={submit}
            disabled={busy}
            data-testid="submit-user"
          >
            {busy ? t("loading") : t("save")}
          </button>
        </>
      }
    >
      {error === null ? null : <ErrorNotice error={error} />}
      <Field
        label={t("username_label")}
        value={username}
        error={verdicts.username}
        required
        onInput={setUsername}
      />
      <Field
        label={t("real_name_label")}
        value={realName}
        error={verdicts.realName}
        required
        onInput={setRealName}
      />
      <Field
        label={t("password_label")}
        type="password"
        value={password}
        error={verdicts.password}
        autoComplete="new-password"
        required
        onInput={setPassword}
      />
      <Field
        label={t("repeat_password_label")}
        type="password"
        value={repeat}
        error={verdicts.repeat}
        autoComplete="new-password"
        required
        onInput={setRepeat}
      />
      <label class="flex items-center gap-2 text-sm text-muted">
        <input
          type="checkbox"
          checked={isAdmin}
          data-testid="is-admin"
          onChange={(event) => setIsAdmin(event.currentTarget.checked)}
        />
        {t("is_admin_column")}
      </label>
    </Modal>
  );
}
