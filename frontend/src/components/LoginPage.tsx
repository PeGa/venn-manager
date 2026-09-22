/** Login page. Authenticates user and redirects to dashboard or password change. */
import { useState } from "preact/hooks";
import { useQueryClient } from "@tanstack/preact-query";
import { login } from "../api/client.ts";
import { useLocale } from "../hooks/useLocale.ts";

export const LoginPage = () => {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const queryClient = useQueryClient();
  const { t } = useLocale();

  const handleSubmit = async (e: Event) => {
    e.preventDefault();
    setError("");
    try {
      await login(username, password);
      await queryClient.invalidateQueries({ queryKey: ["auth"] });
    } catch (err) {
      setError("Invalid credentials");
    }
  };

  return (
    <div class="flex items-center justify-center min-h-screen">
      <form onSubmit={handleSubmit} class="flex flex-col gap-4 p-8 border rounded-lg" style={{ borderColor: "var(--color-border)", background: "var(--color-surface)" }}>
        <h1 class="text-2xl font-bold text-center">{t("__app_title")}</h1>
        {error && <p role="alert" class="text-sm" style={{ color: "var(--color-error)" }}>{error}</p>}
        <label class="flex flex-col gap-1">
          <span>{t("__username")}</span>
          <input
            type="text"
            value={username}
            onInput={(e) => setUsername((e.target as HTMLInputElement).value)}
            class="px-3 py-2 border rounded"
            style={{ borderColor: "var(--color-border)", background: "var(--color-bg)" }}
            autocomplete="username"
            required
          />
        </label>
        <label class="flex flex-col gap-1">
          <span>{t("__password")}</span>
          <input
            type="password"
            value={password}
            onInput={(e) => setPassword((e.target as HTMLInputElement).value)}
            class="px-3 py-2 border rounded"
            style={{ borderColor: "var(--color-border)", background: "var(--color-bg)" }}
            autocomplete="current-password"
            required
          />
        </label>
        <button type="submit" class="px-4 py-2 text-white rounded" style={{ background: "var(--color-primary)" }}>
          {t("__login")}
        </button>
      </form>
    </div>
  );
};
