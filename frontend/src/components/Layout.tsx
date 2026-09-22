/** App layout with hamburger menu navigation. */
import { useState } from "preact/hooks";
import { useLocation } from "wouter-preact";
import { useAuth } from "../hooks/useAuth.ts";
import { useLocale } from "../hooks/useLocale.ts";

interface LayoutProps {
  readonly children: preact.ComponentChildren;
}

export const Layout = ({ children }: LayoutProps) => {
  const [menuOpen, setMenuOpen] = useState(false);
  const { logout } = useAuth();
  const { t } = useLocale();
  const [, navigate] = useLocation();

  const navItems = [
    { label: t("__home"), path: "/" },
    { label: t("__budget"), path: "/budget" },
    { label: t("__concepts"), path: "/concepts" },
    { label: t("__history"), path: "/history" },
    { label: t("__config"), path: "/config" },
  ];

  const handleNav = (path: string) => {
    navigate(path);
    setMenuOpen(false);
  };

  return (
    <div class="min-h-screen" style={{ background: "var(--color-bg)" }}>
      <header class="flex items-center gap-4 p-4 border-b" style={{ borderColor: "var(--color-border)" }}>
        <button
          onClick={() => setMenuOpen(!menuOpen)}
          class="p-2 rounded"
          aria-label="Menu"
          aria-expanded={menuOpen}
        >
          ☰
        </button>
        <h1 class="text-xl font-bold">{t("__app_title")}</h1>
      </header>

      {menuOpen && (
        <nav class="border-b p-4 flex flex-col gap-2" style={{ borderColor: "var(--color-border)", background: "var(--color-surface)" }} role="navigation">
          {navItems.map((item) => (
            <button
              key={item.path}
              onClick={() => handleNav(item.path)}
              class="text-left px-3 py-2 rounded hover:opacity-80"
            >
              {item.label}
            </button>
          ))}
          <button onClick={logout} class="text-left px-3 py-2 rounded hover:opacity-80" style={{ color: "var(--color-error)" }}>
            {t("__logout")}
          </button>
        </nav>
      )}

      <main class="p-4">{children}</main>
    </div>
  );
};
