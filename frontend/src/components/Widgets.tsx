/**
 * The Home dashboard widgets (FRONTEND.md § 1.2).
 *
 * Five figures, in the order the contract lists them: money out so far, money in
 * so far, savings projection, spend projection, earn projection. All five come
 * from one `GET /projections` call — the frontend never recomputes them, because
 * BACKEND.md § 2 makes the backend the single source of the formula.
 *
 * The two projection widgets also carry a secondary line (FRONTEND.md § 1.2.6-7)
 * built from `*_budget_remaining`, because a projection that differs from the
 * actuals reads as a bug unless the screen says why: "12 spent + 7 of budget
 * left" is the whole explanation for a 19.
 */
import { useTranslation, type Translate } from "@/hooks/useTranslation";
import type { TranslationKey } from "@/l10n";
import type { Projections } from "@/types/api";
import { formatMoney } from "@/utils/format";

export interface WidgetsProps {
  projections: Projections | undefined;
  currency: string;
  loading: boolean;
}

interface WidgetSpec {
  key: TranslationKey;
  read: (value: Projections) => number;
  /** Savings may legitimately be negative; the sign must stay visible. */
  signed?: boolean;
  breakdown?: (value: Projections, money: (n: number) => string, t: Translate) => string;
}

export function Widgets({ projections, currency, loading }: WidgetsProps) {
  const t = useTranslation();
  const money = (value: number): string => formatMoney(value, currency);

  const widgets: WidgetSpec[] = [
    { key: "widget_actual_out", read: (p) => p.actual_spend },
    { key: "widget_actual_in", read: (p) => p.actual_earn },
    { key: "widget_savings_projection", read: (p) => p.savings_projection, signed: true },
    {
      key: "widget_spend_projection",
      read: (p) => p.spend_projection,
      breakdown: (p, m, tr) =>
        tr("widget_spend_breakdown", {
          spent: m(p.actual_spend),
          remaining: m(p.spend_budget_remaining),
        }),
    },
    {
      key: "widget_earn_projection",
      read: (p) => p.earn_projection,
      breakdown: (p, m, tr) =>
        p.actual_earn === 0
          ? tr("widget_earn_none")
          : tr("widget_earn_breakdown", {
              booked: m(p.actual_earn),
              remaining: m(p.earn_budget_remaining),
            }),
    },
  ];

  return (
    <ul class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5" data-testid="widgets">
      {widgets.map((widget) => {
        const value = projections === undefined ? null : widget.read(projections);
        const tone =
          value === null || !widget.signed || value >= 0 ? "text-ink" : "text-negative";
        return (
          <li class="vm-card" key={widget.key}>
            <p class="text-xs font-medium uppercase tracking-wide text-muted">
              {t(widget.key)}
            </p>
            <p
              class={`mt-1 text-xl font-semibold tabular-nums ${tone}`}
              data-testid={`widget-${widget.key}`}
            >
              {loading || value === null ? t("loading") : money(value)}
            </p>
            <p
              class="mt-1 min-h-4 text-xs text-muted"
              data-testid={`breakdown-${widget.key}`}
            >
              {loading || value === null || widget.breakdown === undefined || projections === undefined
                ? ""
                : widget.breakdown(projections, money, t)}
            </p>
          </li>
        );
      })}
    </ul>
  );
}
