/** Forced password change page. Shown when must_change_password is true. */
import { useState } from "preact/hooks";
import { useQueryClient } from "@tanstack/preact-query";
import { changePassword } from "../api/client.ts";
import { useLocale } from "../hooks/useLocale.ts";

export const ChangePasswordPage = () => {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [error, setError] = useState("");
  const queryClient = useQueryClient();
  const { t } = useLocale();

  const handleSubmit = async (e: Event) => {
    e.preventDefault();
    setError("");
    try {
      await changePassword(currentPassword, newPassword);
      await queryClient.invalidateQueries({ queryKey: ["auth"] });
    } catch {
      setError("Current password is incorrect");
    }
  };

  return (
    <div class="flex items-center justify-center min-h-screen">
      <form onSubmit={handleSubmit} class="flex flex-col gap-4 p-8 border rounded-lg" style={{ borderColor: "var(--color-border)", background: "var(--color-surface)" }}>
        <h1 class="text-2xl font-bold text-center">{t("__change_password")}</h1>
        {error && <p role="alert" class="text-sm" style={{ color: "var(--color-error)" }}>{error}</p>}
        <label class="flex flex-col gap-1">
          <span>{t("__current_password")}</span>
          <input type="password" value={currentPassword} onInput={(e) => setCurrentPassword((e.target as HTMLInputElement).value)} class="px-3 py-2 border rounded" style={{ borderColor: "var(--color-border)", background: "var(--color-bg)" }} required />
        </label>
        <label class="flex flex-col gap-1">
          <span>{t("__new_password")}</span>
          <input type="password" value={newPassword} onInput={(e) => setNewPassword((e.target as HTMLInputElement).value)} class="px-3 py-2 border rounded" style={{ borderColor: "var(--color-border)", background: "var(--color-bg)" }} required />
        </label>
        <button type="submit" class="px-4 py-2 text-white rounded" style={{ background: "var(--color-primary)" }}>
          {t("__change_password")}
        </button>
      </form>
    </div>
  );
};
