/**
 * History and Budget display rules (FRONTEND.md § 4 and § 2).
 *
 * History: the picker is bounded to earliest…(working month − 1), the working
 * month is what shows on first entry, and an empty range disables the picker with
 * the "No previous months to show" legend.
 *
 * Budget: the stored date is displayed inside the working month with the day
 * clamped, and never rewritten.
 */
import { fireEvent, screen, waitFor } from "@testing-library/preact";
import { describe, expect, it } from "vitest";

import { MonthSwitchProvider } from "@/components/MonthSwitch";
import { BudgetScreen, HistoryScreen } from "@/components/RecordScreens";
import { renderWithProviders, stubApi } from "../helpers";
import type { MoneyRecord } from "@/types/api";

function budgetRow(date: string, amount: number | null): MoneyRecord {
  return {
    id: 1,
    type: "budget",
    date,
    concept_id: 3,
    concept_name: "Rent",
    concept_flow: "out",
    concept_is_deleted: false,
    amount,
    user_id: 1,
    username: "admin",
    user_is_deleted: false,
    created_at: "2025-07-01T08:00:00Z",
  };
}

function stubMonth(state: {
  current_month: string;
  last_acknowledged_month: string;
  needs_switch: boolean;
  earliest_month: string | null;
}) {
  return stubApi([
    { match: /\/current-month$/, data: state },
    { match: /\/settings\/concepts/, data: [] },
    {
      match: /\/records/,
      data: [],
      meta: { page: 1, per_page: 10, total: 0, total_pages: 1 },
    },
  ]);
}

function renderHistory() {
  return renderWithProviders(
    <MonthSwitchProvider enabled>
      <HistoryScreen />
    </MonthSwitchProvider>,
  );
}

const WORKING = "2025-07";

describe("HistoryScreen", () => {
  it("bounds the picker to the months before the working month", async () => {
    stubMonth({
      current_month: WORKING,
      last_acknowledged_month: WORKING,
      needs_switch: false,
      earliest_month: "2025-03",
    });

    renderHistory();
    await waitFor(() =>
      expect(screen.getByTestId("history-shown").textContent).toBe(WORKING),
    );

    const picker = screen.getByTestId("history-month") as HTMLInputElement;
    expect(picker.disabled).toBe(false);
    expect(picker.min).toBe("2025-03");
    // The working month itself is not selectable: the only way to see it is by
    // entering History, which is what the screen starts on.
    expect(picker.max).toBe("2025-06");
    expect(screen.getByTestId("history-shown").textContent).toBe(WORKING);
    expect(screen.queryByTestId("no-previous-months")).toBeNull();
  });

  it("shows the working month before any month is picked", async () => {
    stubMonth({
      current_month: WORKING,
      last_acknowledged_month: WORKING,
      needs_switch: false,
      earliest_month: "2025-05",
    });

    renderHistory();

    await waitFor(() =>
      expect(screen.getByTestId("history-shown").textContent).toBe(WORKING),
    );
  });

  it("switches the grid to the picked month", async () => {
    const fetchMock = stubMonth({
      current_month: WORKING,
      last_acknowledged_month: WORKING,
      needs_switch: false,
      earliest_month: "2025-05",
    });

    renderHistory();
    await waitFor(() =>
      expect(screen.getByTestId("history-shown").textContent).toBe(WORKING),
    );
    const picker = screen.getByTestId("history-month") as HTMLInputElement;

    fireEvent.change(picker, { target: { value: "2025-05" } });

    await waitFor(() =>
      expect(screen.getByTestId("history-shown").textContent).toBe("2025-05"),
    );
    await waitFor(() =>
      expect(
        fetchMock.mock.calls.some(([url]) => String(url).includes("month=2025-05")),
      ).toBe(true),
    );
  });

  it("disables the picker and explains why when there is no history", async () => {
    stubMonth({
      current_month: WORKING,
      last_acknowledged_month: WORKING,
      needs_switch: false,
      earliest_month: null,
    });

    renderHistory();

    await screen.findByTestId("no-previous-months");

    const picker = screen.getByTestId("history-month") as HTMLInputElement;
    expect(picker.disabled).toBe(true);
    expect(screen.getByTestId("no-previous-months").textContent).toBe(
      "No previous months to show",
    );
    // Still shows the working month, read only.
    expect(screen.getByTestId("history-shown").textContent).toBe(WORKING);
  });

  it("treats a single recorded month as having no history", async () => {
    stubMonth({
      current_month: WORKING,
      last_acknowledged_month: WORKING,
      needs_switch: false,
      earliest_month: WORKING,
    });

    renderHistory();

    expect(await screen.findByTestId("no-previous-months")).toBeTruthy();
  });

  it("does not claim there is no history while the state is still loading", () => {
    // Regression: the legend used to render on the first paint, before the month
    // query resolved, so every visit briefly said there was nothing to show.
    stubMonth({
      current_month: WORKING,
      last_acknowledged_month: WORKING,
      needs_switch: false,
      earliest_month: null,
    });

    renderHistory();

    expect(screen.getByTestId("history-shown").textContent).toBe("");
    expect(screen.queryByTestId("no-previous-months")).toBeNull();
  });

  it("is read only", async () => {
    stubMonth({
      current_month: WORKING,
      last_acknowledged_month: WORKING,
      needs_switch: false,
      earliest_month: "2025-05",
    });

    renderHistory();
    await waitFor(() =>
      expect(screen.getByTestId("history-shown").textContent).toBe(WORKING),
    );

    expect(screen.queryByTestId("add-record")).toBeNull();
    expect(screen.queryByTestId("delete-selected")).toBeNull();
  });
});

describe("BudgetScreen", () => {
  function renderBudget(rows: MoneyRecord[]) {
    stubApi([
      {
        match: /\/current-month$/,
        data: {
          current_month: WORKING,
          last_acknowledged_month: WORKING,
          needs_switch: false,
          earliest_month: "2025-01",
        },
      },
      { match: /\/settings\/concepts/, data: [] },
      {
        match: /\/records/,
        data: rows,
        meta: { page: 1, per_page: 10, total: rows.length, total_pages: 1 },
      },
    ]);
    return renderWithProviders(
      <MonthSwitchProvider enabled>
        <BudgetScreen />
      </MonthSwitchProvider>,
    );
  }

  it("shows a stored date inside the working month", async () => {
    renderBudget([budgetRow("2025-01-31", 900)]);

    await waitFor(() => expect(screen.getByText("2025-07-31")).toBeTruthy());
    // The stored date is a display input only; it is never shown as-is here.
    expect(screen.queryByText("2025-01-31")).toBeNull();
  });

  it("keeps the stored day and only clamps it", async () => {
    // FRONTEND.md § 2: a budget on the 31st shows as the 28th in February and as
    // the 31st again in March. Clamping is a transform, not a rewrite.
    renderBudget([budgetRow("2025-02-28", 10)]);

    await waitFor(() => expect(screen.getByText("2025-07-28")).toBeTruthy());
  });

  it("renders an unreserved budget amount as empty, not as zero", async () => {
    renderBudget([budgetRow("2025-01-31", null)]);

    await waitFor(() => expect(screen.getByText("Rent")).toBeTruthy());
    expect(screen.queryByText("0.00")).toBeNull();
  });

  it("still offers the record actions", async () => {
    renderBudget([budgetRow("2025-01-31", 900)]);

    await waitFor(() => expect(screen.getByTestId("add-record")).toBeTruthy());
    expect(screen.getByTestId("delete-selected")).toBeTruthy();
  });
});
