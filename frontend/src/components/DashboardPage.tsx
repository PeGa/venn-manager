/** Home/Dashboard page. Shows projection widgets and transaction grid. */
import { useState } from "preact/hooks";
import { useQuery, useQueryClient } from "@tanstack/preact-query";
import { getRecords, getProjections, createRecord, deleteRecord, getConcepts } from "../api/client.ts";
import { getCurrentMonth, getToday, formatAmount } from "../utils/format.ts";
import { useLocale } from "../hooks/useLocale.ts";
import { Layout } from "./Layout.tsx";

export const DashboardPage = () => {
  const month = getCurrentMonth();
  const { t } = useLocale();
  const queryClient = useQueryClient();
  const [filter, setFilter] = useState("");
  const [showAdd, setShowAdd] = useState(false);

  const { data: recordsData } = useQuery({
    queryKey: ["records", month, filter],
    queryFn: () => getRecords(month, filter || undefined),
  });

  const { data: projections } = useQuery({
    queryKey: ["projections", month],
    queryFn: () => getProjections(month),
  });

  const records = recordsData?.records ?? [];

  return (
    <Layout>
      {/* Projection Widgets */}
      <div class="grid grid-cols-2 gap-3 mb-6 sm:grid-cols-3 lg:grid-cols-5">
        <Widget label={t("__current_out")} value={projections ? formatAmount(projections.current_out) : "—"} />
        <Widget label={t("__current_in")} value={projections ? formatAmount(projections.current_in) : "—"} />
        <Widget label={t("__savings_projection")} value={projections ? formatAmount(projections.savings_projection) : "—"} />
        <Widget label={t("__spend_projection")} value={projections ? formatAmount(projections.spend_projection) : "—"} />
        <Widget label={t("__earn_projection")} value={projections ? formatAmount(projections.earn_projection) : "—"} />
      </div>

      {/* Toolbar */}
      <div class="flex gap-2 mb-4">
        <button onClick={() => setShowAdd(true)} class="px-3 py-1 text-white rounded text-sm" style={{ background: "var(--color-primary)" }}>
          {t("__add")}
        </button>
        <input
          type="text"
          placeholder={t("__search")}
          value={filter}
          onInput={(e) => setFilter((e.target as HTMLInputElement).value)}
          class="px-3 py-1 border rounded text-sm flex-1"
          style={{ borderColor: "var(--color-border)", background: "var(--color-bg)" }}
        />
      </div>

      {/* Transaction Grid */}
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b" style={{ borderColor: "var(--color-border)" }}>
            <th class="text-left py-2 px-2">{t("__date")}</th>
            <th class="text-left py-2 px-2">{t("__concept")}</th>
            <th class="text-right py-2 px-2">{t("__amount")}</th>
            <th class="text-left py-2 px-2">{t("__flow")}</th>
            <th class="text-left py-2 px-2">{t("__user")}</th>
            <th class="py-2 px-2"></th>
          </tr>
        </thead>
        <tbody>
          {records.map((r) => (
            <tr key={r.id} class="border-b" style={{ borderColor: "var(--color-border)" }}>
              <td class="py-2 px-2">{r.date}</td>
              <td class="py-2 px-2">{r.concept_name}</td>
              <td class="py-2 px-2 text-right">{formatAmount(r.amount)}</td>
              <td class="py-2 px-2">{r.flow === "IN" ? t("__in") : t("__out")}</td>
              <td class="py-2 px-2">{r.username}</td>
              <td class="py-2 px-2">
                <button onClick={async () => { await deleteRecord(r.id); queryClient.invalidateQueries({ queryKey: ["records"] }); queryClient.invalidateQueries({ queryKey: ["projections"] }); }} class="text-sm" style={{ color: "var(--color-error)" }} aria-label={`${t("__delete")} ${r.concept_name}`}>
                  ✕
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {showAdd && <AddRecordModal onClose={() => setShowAdd(false)} />}
    </Layout>
  );
};

const Widget = ({ label, value }: { label: string; value: string }) => (
  <div class="p-3 rounded border" style={{ borderColor: "var(--color-border)", background: "var(--color-surface)" }}>
    <div class="text-xs opacity-70">{label}</div>
    <div class="text-lg font-bold">{value}</div>
  </div>
);

const AddRecordModal = ({ onClose }: { onClose: () => void }) => {
  const { t } = useLocale();
  const queryClient = useQueryClient();
  const [date, setDate] = useState(getToday());
  const [conceptId, setConceptId] = useState(0);
  const [amount, setAmount] = useState("");

  const { data: conceptsData } = useQuery({
    queryKey: ["concepts"],
    queryFn: () => getConcepts(),
  });
  const concepts = conceptsData?.concepts ?? [];

  const handleSubmit = async (e: Event) => {
    e.preventDefault();
    if (!conceptId || !amount) return;
    await createRecord(date, conceptId, parseFloat(amount));
    queryClient.invalidateQueries({ queryKey: ["records"] });
    queryClient.invalidateQueries({ queryKey: ["projections"] });
    onClose();
  };

  return (
    <div class="fixed inset-0 flex items-center justify-center" style={{ background: "rgba(0,0,0,0.5)" }} role="dialog" aria-modal="true">
      <form onSubmit={handleSubmit} class="flex flex-col gap-4 p-6 rounded-lg border w-80" style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}>
        <h2 class="text-lg font-bold">{t("__add")}</h2>
        <label class="flex flex-col gap-1">
          <span>{t("__date")}</span>
          <input type="date" value={date} onInput={(e) => setDate((e.target as HTMLInputElement).value)} class="px-3 py-2 border rounded" style={{ borderColor: "var(--color-border)", background: "var(--color-bg)" }} required />
        </label>
        <label class="flex flex-col gap-1">
          <span>{t("__concept")}</span>
          <select value={conceptId} onChange={(e) => setConceptId(Number((e.target as HTMLSelectElement).value))} class="px-3 py-2 border rounded" style={{ borderColor: "var(--color-border)", background: "var(--color-bg)" }} required>
            <option value={0}>—</option>
            {concepts.map((c) => (
              <option key={c.id} value={c.id}>{c.name} ({c.flow})</option>
            ))}
          </select>
        </label>
        <label class="flex flex-col gap-1">
          <span>{t("__amount")}</span>
          <input type="number" step="0.01" min="0" value={amount} onInput={(e) => setAmount((e.target as HTMLInputElement).value)} class="px-3 py-2 border rounded" style={{ borderColor: "var(--color-border)", background: "var(--color-bg)" }} required />
        </label>
        <div class="flex gap-2 justify-end">
          <button type="button" onClick={onClose} class="px-3 py-2 border rounded text-sm">{t("__cancel")}</button>
          <button type="submit" class="px-3 py-2 text-white rounded text-sm" style={{ background: "var(--color-primary)" }}>{t("__save")}</button>
        </div>
      </form>
    </div>
  );
};
