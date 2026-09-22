/** History page. Read-only view of past months' transactions. */
import { useState } from "preact/hooks";
import { useQuery } from "@tanstack/preact-query";
import { getHistory, getHistoryMonths } from "../api/client.ts";
import { formatAmount } from "../utils/format.ts";
import { useLocale } from "../hooks/useLocale.ts";
import { Layout } from "./Layout.tsx";

export const HistoryPage = () => {
  const { t } = useLocale();
  const [selectedMonth, setSelectedMonth] = useState("");

  const { data: monthsData } = useQuery({
    queryKey: ["historyMonths"],
    queryFn: getHistoryMonths,
  });

  const months = monthsData?.months ?? [];
  const effectiveMonth = selectedMonth || (months.length > 0 ? months[0] : "");

  const { data: historyData } = useQuery({
    queryKey: ["history", effectiveMonth],
    queryFn: () => getHistory(effectiveMonth),
    enabled: effectiveMonth !== "",
  });

  const records = historyData?.records ?? [];

  return (
    <Layout>
      <div class="mb-4">
        <select
          value={effectiveMonth}
          onChange={(e) => setSelectedMonth((e.target as HTMLSelectElement).value)}
          class="px-3 py-2 border rounded"
          style={{ borderColor: "var(--color-border)", background: "var(--color-bg)" }}
        >
          {months.length === 0 && (
            <option value="" disabled>{t("__no_previous_months")}</option>
          )}
          {months.map((m) => (
            <option key={m} value={m}>{m}</option>
          ))}
        </select>
      </div>

      {effectiveMonth && (
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b" style={{ borderColor: "var(--color-border)" }}>
              <th class="text-left py-2 px-2">{t("__date")}</th>
              <th class="text-left py-2 px-2">{t("__concept")}</th>
              <th class="text-right py-2 px-2">{t("__amount")}</th>
              <th class="text-left py-2 px-2">{t("__flow")}</th>
              <th class="text-left py-2 px-2">{t("__user")}</th>
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
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Layout>
  );
};
