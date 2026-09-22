/** Configuration page. Profile settings and admin user management. */
import { useState } from "preact/hooks";
import { useQuery, useQueryClient } from "@tanstack/preact-query";
import { getUsers, createUser, deleteUser, setCurrency, setLanguage, setTheme, changePassword } from "../api/client.ts";
import { useAuth } from "../hooks/useAuth.ts";
import { useSettings } from "../hooks/useSettings.ts";
import { useLocale } from "../hooks/useLocale.ts";
import { Layout } from "./Layout.tsx";

export const ConfigPage = () => {
  const { t } = useLocale();
  const { user } = useAuth();
  const { settings } = useSettings();
  const queryClient = useQueryClient();

  // Profile state
  const [realName, setRealName] = useState(user?.real_name ?? "");
  const [language, setLanguageState] = useState(user?.language ?? "en");
  const [currency, setCurrencyState] = useState(settings?.currency ?? "$");
  const [theme, setThemeState] = useState(user?.theme ?? "system");
  const [currentPw, setCurrentPw] = useState("");
  const [newPw, setNewPw] = useState("");

  const handleSaveProfile = async () => {
    await setLanguage(language);
    await setTheme(theme);
    if (newPw && currentPw) {
      await changePassword(currentPw, newPw);
      setCurrentPw("");
      setNewPw("");
    }
    queryClient.invalidateQueries({ queryKey: ["auth"] });
    queryClient.invalidateQueries({ queryKey: ["settings"] });
  };

  const handleCurrencyChange = async () => {
    if (confirm(t("__currency_change_warning"))) {
      await setCurrency(currency);
      queryClient.invalidateQueries({ queryKey: ["settings"] });
    }
  };

  return (
    <Layout>
      <h2 class="text-xl font-bold mb-4">{t("__profile")}</h2>
      <div class="flex flex-col gap-3 max-w-md mb-8">
        <label class="flex flex-col gap-1">
          <span>{t("__real_name")}</span>
          <input type="text" value={realName} onInput={(e) => setRealName((e.target as HTMLInputElement).value)} class="px-3 py-2 border rounded" style={{ borderColor: "var(--color-border)", background: "var(--color-bg)" }} />
        </label>
        <label class="flex flex-col gap-1">
          <span>{t("__language")}</span>
          <select value={language} onChange={(e) => setLanguageState((e.target as HTMLSelectElement).value)} class="px-3 py-2 border rounded" style={{ borderColor: "var(--color-border)", background: "var(--color-bg)" }}>
            <option value="en">English</option>
            <option value="es">Español</option>
          </select>
        </label>
        <label class="flex flex-col gap-1">
          <span>{t("__currency")}</span>
          <div class="flex gap-2">
            <input type="text" maxLength={10} value={currency} onInput={(e) => setCurrencyState((e.target as HTMLInputElement).value)} class="px-3 py-2 border rounded flex-1" style={{ borderColor: "var(--color-border)", background: "var(--color-bg)" }} />
            <button onClick={handleCurrencyChange} class="px-3 py-2 text-white rounded text-sm" style={{ background: "var(--color-primary)" }}>{t("__save")}</button>
          </div>
        </label>
        <label class="flex flex-col gap-1">
          <span>{t("__theme")}</span>
          <select value={theme} onChange={(e) => setThemeState((e.target as HTMLSelectElement).value)} class="px-3 py-2 border rounded" style={{ borderColor: "var(--color-border)", background: "var(--color-bg)" }}>
            <option value="light">{t("__light")}</option>
            <option value="dark">{t("__dark")}</option>
            <option value="system">{t("__system")}</option>
          </select>
        </label>
        <label class="flex flex-col gap-1">
          <span>{t("__current_password")}</span>
          <input type="password" value={currentPw} onInput={(e) => setCurrentPw((e.target as HTMLInputElement).value)} class="px-3 py-2 border rounded" style={{ borderColor: "var(--color-border)", background: "var(--color-bg)" }} />
        </label>
        <label class="flex flex-col gap-1">
          <span>{t("__new_password")}</span>
          <input type="password" value={newPw} onInput={(e) => setNewPw((e.target as HTMLInputElement).value)} class="px-3 py-2 border rounded" style={{ borderColor: "var(--color-border)", background: "var(--color-bg)" }} />
        </label>
        <button onClick={handleSaveProfile} class="px-4 py-2 text-white rounded" style={{ background: "var(--color-primary)" }}>
          {t("__save")}
        </button>
      </div>

      {user?.is_admin && <UserManagement />}
    </Layout>
  );
};

const UserManagement = () => {
  const { t } = useLocale();
  const queryClient = useQueryClient();
  const [showAdd, setShowAdd] = useState(false);

  const { data: usersData } = useQuery({
    queryKey: ["users"],
    queryFn: getUsers,
  });

  const users = usersData?.users ?? [];

  return (
    <div>
      <div class="flex gap-2 mb-4 items-center">
        <h2 class="text-xl font-bold">{t("__management")}</h2>
        <button onClick={() => setShowAdd(true)} class="px-3 py-1 text-white rounded text-sm" style={{ background: "var(--color-primary)" }}>
          {t("__add")}
        </button>
      </div>

      <table class="w-full text-sm">
        <thead>
          <tr class="border-b" style={{ borderColor: "var(--color-border)" }}>
            <th class="text-left py-2 px-2">{t("__username")}</th>
            <th class="text-left py-2 px-2">{t("__real_name")}</th>
            <th class="text-left py-2 px-2">{t("__is_admin")}</th>
            <th class="py-2 px-2"></th>
          </tr>
        </thead>
        <tbody>
          {users.map((u) => (
            <tr key={u.id} class="border-b" style={{ borderColor: "var(--color-border)" }}>
              <td class="py-2 px-2">{u.username}</td>
              <td class="py-2 px-2">{u.real_name}</td>
              <td class="py-2 px-2">{u.is_admin ? "✓" : ""}</td>
              <td class="py-2 px-2">
                <button onClick={async () => { await deleteUser(u.id); queryClient.invalidateQueries({ queryKey: ["users"] }); }} class="text-sm" style={{ color: "var(--color-error)" }} aria-label={`${t("__delete")} ${u.username}`}>
                  ✕
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {showAdd && <AddUserModal onClose={() => setShowAdd(false)} />}
    </div>
  );
};

const AddUserModal = ({ onClose }: { onClose: () => void }) => {
  const { t } = useLocale();
  const queryClient = useQueryClient();
  const [username, setUsername] = useState("");
  const [realName, setRealName] = useState("");
  const [password, setPassword] = useState("");
  const [repeatPassword, setRepeatPassword] = useState("");
  const [isAdmin, setIsAdmin] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: Event) => {
    e.preventDefault();
    if (password !== repeatPassword) {
      setError("Passwords do not match");
      return;
    }
    try {
      await createUser(username.trim(), realName.trim(), password, isAdmin);
      queryClient.invalidateQueries({ queryKey: ["users"] });
      onClose();
    } catch (err) {
      const apiErr = err as { detail?: string };
      setError(apiErr.detail ?? "Failed to create user");
    }
  };

  return (
    <div class="fixed inset-0 flex items-center justify-center" style={{ background: "rgba(0,0,0,0.5)" }} role="dialog" aria-modal="true">
      <form onSubmit={handleSubmit} class="flex flex-col gap-4 p-6 rounded-lg border w-80" style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}>
        <h2 class="text-lg font-bold">{t("__add")}</h2>
        {error && <p role="alert" class="text-sm" style={{ color: "var(--color-error)" }}>{error}</p>}
        <label class="flex flex-col gap-1">
          <span>{t("__username")}</span>
          <input type="text" value={username} onInput={(e) => setUsername((e.target as HTMLInputElement).value)} class="px-3 py-2 border rounded" style={{ borderColor: "var(--color-border)", background: "var(--color-bg)" }} required />
        </label>
        <label class="flex flex-col gap-1">
          <span>{t("__real_name")}</span>
          <input type="text" value={realName} onInput={(e) => setRealName((e.target as HTMLInputElement).value)} class="px-3 py-2 border rounded" style={{ borderColor: "var(--color-border)", background: "var(--color-bg)" }} required />
        </label>
        <label class="flex flex-col gap-1">
          <span>{t("__password")}</span>
          <input type="password" value={password} onInput={(e) => setPassword((e.target as HTMLInputElement).value)} class="px-3 py-2 border rounded" style={{ borderColor: "var(--color-border)", background: "var(--color-bg)" }} required />
        </label>
        <label class="flex flex-col gap-1">
          <span>{t("__repeat_password")}</span>
          <input type="password" value={repeatPassword} onInput={(e) => setRepeatPassword((e.target as HTMLInputElement).value)} class="px-3 py-2 border rounded" style={{ borderColor: "var(--color-border)", background: "var(--color-bg)" }} required />
        </label>
        <label class="flex items-center gap-2">
          <input type="checkbox" checked={isAdmin} onChange={(e) => setIsAdmin((e.target as HTMLInputElement).checked)} />
          <span>{t("__is_admin")}</span>
        </label>
        <div class="flex gap-2 justify-end">
          <button type="button" onClick={onClose} class="px-3 py-2 border rounded text-sm">{t("__cancel")}</button>
          <button type="submit" class="px-3 py-2 text-white rounded text-sm" style={{ background: "var(--color-primary)" }}>{t("__save")}</button>
        </div>
      </form>
    </div>
  );
};
