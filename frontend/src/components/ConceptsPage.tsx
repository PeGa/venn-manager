/** Concepts page. Manage accounting concepts (categories). */
import { useState } from "preact/hooks";
import { useQuery, useQueryClient } from "@tanstack/preact-query";
import { getConcepts, createConcept, deleteConcept } from "../api/client.ts";
import { useLocale } from "../hooks/useLocale.ts";
import { Layout } from "./Layout.tsx";

export const ConceptsPage = () => {
  const { t } = useLocale();
  const queryClient = useQueryClient();
  const [filter, setFilter] = useState("");
  const [showAdd, setShowAdd] = useState(false);

  const { data: conceptsData } = useQuery({
    queryKey: ["concepts", filter],
    queryFn: () => getConcepts(filter || undefined),
  });

  const concepts = conceptsData?.concepts ?? [];

  return (
    <Layout>
      <div class="flex gap-2 mb-4">
        <button onClick={() => setShowAdd(true)} class="px-3 py-1 text-white rounded text-sm" style={{ background: "var(--color-primary)" }}>
          {t("__add")}
        </button>
        <input type="text" placeholder={t("__search")} value={filter} onInput={(e) => setFilter((e.target as HTMLInputElement).value)} class="px-3 py-1 border rounded text-sm flex-1" style={{ borderColor: "var(--color-border)", background: "var(--color-bg)" }} />
      </div>

      <table class="w-full text-sm">
        <thead>
          <tr class="border-b" style={{ borderColor: "var(--color-border)" }}>
            <th class="text-left py-2 px-2">{t("__date")}</th>
            <th class="text-left py-2 px-2">{t("__concept")}</th>
            <th class="text-left py-2 px-2">{t("__flow")}</th>
            <th class="text-left py-2 px-2">{t("__user")}</th>
            <th class="py-2 px-2"></th>
          </tr>
        </thead>
        <tbody>
          {concepts.map((c) => (
            <tr key={c.id} class="border-b" style={{ borderColor: "var(--color-border)" }}>
              <td class="py-2 px-2">{c.created_at.split("T")[0]}</td>
              <td class="py-2 px-2">{c.name}</td>
              <td class="py-2 px-2">{c.flow === "IN" ? t("__in") : t("__out")}</td>
              <td class="py-2 px-2">{c.username}</td>
              <td class="py-2 px-2">
                <button onClick={async () => { await deleteConcept(c.id); queryClient.invalidateQueries({ queryKey: ["concepts"] }); }} class="text-sm" style={{ color: "var(--color-error)" }} aria-label={`${t("__delete")} ${c.name}`}>
                  ✕
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {showAdd && <AddConceptModal onClose={() => setShowAdd(false)} />}
    </Layout>
  );
};

const AddConceptModal = ({ onClose }: { onClose: () => void }) => {
  const { t } = useLocale();
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [flow, setFlow] = useState<"IN" | "OUT">("IN");

  const handleSubmit = async (e: Event) => {
    e.preventDefault();
    if (!name.trim()) return;
    await createConcept(name.trim(), flow);
    queryClient.invalidateQueries({ queryKey: ["concepts"] });
    onClose();
  };

  return (
    <div class="fixed inset-0 flex items-center justify-center" style={{ background: "rgba(0,0,0,0.5)" }} role="dialog" aria-modal="true">
      <form onSubmit={handleSubmit} class="flex flex-col gap-4 p-6 rounded-lg border w-80" style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}>
        <h2 class="text-lg font-bold">{t("__add")}</h2>
        <label class="flex flex-col gap-1">
          <span>{t("__concept")}</span>
          <input type="text" maxLength={64} value={name} onInput={(e) => setName((e.target as HTMLInputElement).value)} class="px-3 py-2 border rounded" style={{ borderColor: "var(--color-border)", background: "var(--color-bg)" }} required />
        </label>
        <label class="flex flex-col gap-1">
          <span>{t("__flow")}</span>
          <select value={flow} onChange={(e) => setFlow((e.target as HTMLSelectElement).value as "IN" | "OUT")} class="px-3 py-2 border rounded" style={{ borderColor: "var(--color-border)", background: "var(--color-bg)" }}>
            <option value="IN">{t("__in")}</option>
            <option value="OUT">{t("__out")}</option>
          </select>
        </label>
        <div class="flex gap-2 justify-end">
          <button type="button" onClick={onClose} class="px-3 py-2 border rounded text-sm">{t("__cancel")}</button>
          <button type="submit" class="px-3 py-2 text-white rounded text-sm" style={{ background: "var(--color-primary)" }}>{t("__save")}</button>
        </div>
      </form>
    </div>
  );
};
