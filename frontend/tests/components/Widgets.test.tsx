/**
 * Projection display tests (AGENTS.md § TDD: required for projection displays).
 *
 * The frontend never recomputes a projection — BACKEND.md § 2 makes the server
 * the single source of the formula — so what is under test here is that all five
 * figures are shown, labelled, and formatted with two decimals and the currency.
 */
import { screen } from "@testing-library/preact";
import { describe, expect, it } from "vitest";

import { Widgets } from "@/components/Widgets";
import { renderWithProviders } from "../helpers";
import type { Projections } from "@/types/api";

const SAMPLE: Projections = {
  spend_projection: 1250,
  earn_projection: 3000,
  savings_projection: 1750,
  actual_spend: 830.5,
  actual_earn: 3000,
  spend_budget_remaining: 419.5,
  earn_budget_remaining: 0,
};

describe("Widgets", () => {
  it("renders all five figures with the currency and two decimals", () => {
    renderWithProviders(
      <Widgets projections={SAMPLE} currency="$" loading={false} />,
    );

    expect(screen.getByTestId("widget-widget_actual_out").textContent).toBe("$830.50");
    expect(screen.getByTestId("widget-widget_actual_in").textContent).toBe("$3000.00");
    expect(screen.getByTestId("widget-widget_savings_projection").textContent).toBe(
      "$1750.00",
    );
    expect(screen.getByTestId("widget-widget_spend_projection").textContent).toBe(
      "$1250.00",
    );
    expect(screen.getByTestId("widget-widget_earn_projection").textContent).toBe(
      "$3000.00",
    );
  });

  it("labels every widget in the active locale", () => {
    renderWithProviders(<Widgets projections={SAMPLE} currency="€" loading={false} />, "es");

    expect(screen.getByText("Gastado hasta ahora")).toBeTruthy();
    expect(screen.getByText("Proyección de ahorro")).toBeTruthy();
    expect(screen.getByTestId("widget-widget_spend_projection").textContent).toBe(
      "€1250.00",
    );
  });

  it("shows a loading state instead of a stale number", () => {
    renderWithProviders(<Widgets projections={undefined} currency="$" loading />);

    expect(screen.getByTestId("widget-widget_actual_out").textContent).toBe("Loading…");
  });

  it("keeps the sign on a negative savings projection", () => {
    renderWithProviders(
      <Widgets
        projections={{ ...SAMPLE, savings_projection: -1750 }}
        currency="$"
        loading={false}
      />,
    );

    const savings = screen.getByTestId("widget-widget_savings_projection");
    expect(savings.textContent).toBe("$-1750.00");
    expect(savings.className).toContain("text-negative");
  });

  it("does not colour-code a positive savings projection as a loss", () => {
    renderWithProviders(
      <Widgets projections={SAMPLE} currency="$" loading={false} />,
    );

    expect(
      screen.getByTestId("widget-widget_savings_projection").className,
    ).not.toContain("text-negative");
  });

  it("explains the spend projection as spent plus unspent budget", () => {
    // FRONTEND.md § 1.2.6: the number alone reads as a bug; the sub-line is the
    // explanation. 830.50 + 419.50 is exactly the 1250.00 above it.
    renderWithProviders(
      <Widgets projections={SAMPLE} currency="$" loading={false} />,
    );

    expect(screen.getByTestId("breakdown-widget_spend_projection").textContent).toBe(
      "$830.50 spent + $419.50 of budget left",
    );
  });

  it("explains the earn projection as booked plus still expected", () => {
    renderWithProviders(
      <Widgets projections={SAMPLE} currency="$" loading={false} />,
    );

    expect(screen.getByTestId("breakdown-widget_earn_projection").textContent).toBe(
      "$3000.00 booked + $0.00 still expected",
    );
  });

  it("says income has not been booked when nothing has", () => {
    renderWithProviders(
      <Widgets
        projections={{ ...SAMPLE, actual_earn: 0, earn_budget_remaining: 3000 }}
        currency="$"
        loading={false}
      />,
    );

    expect(screen.getByTestId("breakdown-widget_earn_projection").textContent).toBe(
      "no income booked yet",
    );
  });

  it("translates the breakdown", () => {
    renderWithProviders(
      <Widgets projections={SAMPLE} currency="€" loading={false} />,
      "es",
    );

    expect(screen.getByTestId("breakdown-widget_spend_projection").textContent).toBe(
      "€830.50 gastado + €419.50 de presupuesto pendiente",
    );
  });

  it("leaves the non-projection widgets without a breakdown", () => {
    renderWithProviders(
      <Widgets projections={SAMPLE} currency="$" loading={false} />,
    );

    expect(screen.getByTestId("breakdown-widget_actual_out").textContent).toBe("");
    expect(screen.getByTestId("breakdown-widget_savings_projection").textContent).toBe("");
  });
});
