/**
 * Record form validation in the UI (AGENTS.md § TDD: required for form
 * validation logic).
 *
 * The validators themselves are covered in tests/utils/validation.test.ts. What
 * is covered here is that the grid actually runs them: errors appear inline next
 * to the field, and nothing is submitted until the form is valid.
 */
import { fireEvent, screen, waitFor } from "@testing-library/preact";
import { describe, expect, it } from "vitest";

import { RecordGrid } from "@/components/RecordGrid";
import { renderWithProviders, stubApi } from "../helpers";
import type { Concept, MoneyRecord } from "@/types/api";

const CONCEPTS: Concept[] = [
  {
    id: 3,
    name: "Groceries",
    flow: "out",
    created_by: "admin",
    created_by_is_deleted: false,
    created_at: "2025-07-01T08:00:00Z",
    is_deleted: false,
  },
  {
    id: 4,
    name: "Salary",
    flow: "in",
    created_by: "admin",
    created_by_is_deleted: false,
    created_at: "2025-07-01T08:00:00Z",
    is_deleted: false,
  },
];

const ROWS: MoneyRecord[] = [
  {
    id: 1,
    type: "transaction",
    date: "2025-07-15",
    concept_id: 3,
    concept_name: "Groceries",
    concept_flow: "out",
    concept_is_deleted: false,
    amount: 45.5,
    user_id: 1,
    username: "admin",
    user_is_deleted: false,
    created_at: "2025-07-15T10:30:00Z",
  },
];

function stubGrid(): ReturnType<typeof stubApi> {
  return stubApi([
    { match: /\/settings\/concepts/, data: CONCEPTS },
    {
      match: /\/records/,
      data: ROWS,
      meta: { page: 1, per_page: 10, total: 1, total_pages: 1 },
    },
  ]);
}

function renderGrid() {
  return renderWithProviders(
    <RecordGrid
      type="transaction"
      month="2025-07"
      defaultDate="2025-07-15"
      caption="Home"
    />,
  );
}

describe("RecordGrid add form", () => {
  it("lists the stored records", async () => {
    stubGrid();

    renderGrid();

    await waitFor(() => expect(screen.getByText("Groceries")).toBeTruthy());
    expect(screen.getByText("45.50")).toBeTruthy();
  });

  it("refuses an empty submission and posts nothing", async () => {
    const fetchMock = stubGrid();
    renderGrid();
    await waitFor(() => expect(screen.getByText("Groceries")).toBeTruthy());

    fireEvent.click(screen.getByTestId("add-record"));
    fireEvent.click(screen.getByTestId("submit-record"));

    expect(screen.getAllByText("This field is required.").length).toBeGreaterThan(0);
    const posted = fetchMock.mock.calls.find(
      ([url, init]) =>
        String(url).endsWith("/records") &&
        (init as RequestInit | undefined)?.method === "POST",
    );
    expect(posted).toBeUndefined();
  });

  it("rejects an amount with too many decimals", async () => {
    const fetchMock = stubGrid();
    renderGrid();
    await waitFor(() => expect(screen.getByText("Groceries")).toBeTruthy());

    fireEvent.click(screen.getByTestId("add-record"));
    fireEvent.change(screen.getByLabelText("Concept"), { target: { value: "3" } });
    fireEvent.input(screen.getByLabelText("Amount"), {
      target: { value: "45.567" },
    });
    fireEvent.click(screen.getByTestId("submit-record"));

    expect(
      screen.getByText("Enter an amount with at most two decimals."),
    ).toBeTruthy();
    expect(
      fetchMock.mock.calls.find(
        ([url, init]) =>
          String(url).endsWith("/records") &&
          (init as RequestInit | undefined)?.method === "POST",
      ),
    ).toBeUndefined();
  });

  it("accepts a valid transaction and posts it", async () => {
    const fetchMock = stubApi([
      { match: /\/settings\/concepts/, data: CONCEPTS },
      { match: /\/records/, method: "POST", status: 201, data: ROWS[0] },
      {
        match: /\/records/,
        data: ROWS,
        meta: { page: 1, per_page: 10, total: 1, total_pages: 1 },
      },
    ]);
    renderGrid();
    await waitFor(() => expect(screen.getByText("Groceries")).toBeTruthy());

    fireEvent.click(screen.getByTestId("add-record"));
    fireEvent.change(screen.getByLabelText("Concept"), { target: { value: "3" } });
    fireEvent.input(screen.getByLabelText("Amount"), { target: { value: "45.50" } });
    fireEvent.click(screen.getByTestId("submit-record"));

    await waitFor(() => {
      const posted = fetchMock.mock.calls.find(
        ([url, init]) =>
          String(url).endsWith("/records") &&
          (init as RequestInit | undefined)?.method === "POST",
      );
      expect(posted).toBeTruthy();
      expect(JSON.parse(String((posted?.[1] as RequestInit).body))).toEqual({
        type: "transaction",
        date: "2025-07-15",
        concept_id: 3,
        amount: "45.50",
      });
    });
  });

  it("derives the flow from the concept and offers no way to pick it", async () => {
    stubGrid();
    renderGrid();
    await waitFor(() => expect(screen.getByText("Groceries")).toBeTruthy());

    fireEvent.click(screen.getByTestId("add-record"));
    // FRONTEND.md § 1.1.1: flow is auto-populated and not manually selectable.
    expect(screen.queryByLabelText("Flow")).toBeNull();
    expect(screen.getByTestId("flow-preview").textContent).toBe("Flow: —");

    fireEvent.change(screen.getByLabelText("Concept"), { target: { value: "4" } });

    expect(screen.getByTestId("flow-preview").textContent).toContain("In");
  });
});

describe("RecordGrid inline edit", () => {
  it("validates the edited amount before saving", async () => {
    const fetchMock = stubGrid();
    renderGrid();
    await waitFor(() => expect(screen.getByText("Groceries")).toBeTruthy());

    fireEvent.click(screen.getByTestId("edit-1"));
    const amount = screen.getByLabelText("Amount");
    fireEvent.input(amount, { target: { value: "not-a-number" } });
    fireEvent.click(screen.getByTestId("save-1"));

    expect(
      screen.getByText("Enter an amount with at most two decimals."),
    ).toBeTruthy();
    expect(
      fetchMock.mock.calls.find(
        ([, init]) => (init as RequestInit | undefined)?.method === "PATCH",
      ),
    ).toBeUndefined();
  });

  it("prefills the inline form from the stored record", async () => {
    stubGrid();
    renderGrid();
    await waitFor(() => expect(screen.getByText("Groceries")).toBeTruthy());

    fireEvent.click(screen.getByTestId("edit-1"));

    const amount = screen.getByLabelText("Amount") as HTMLInputElement;
    expect(amount.value).toBe("45.5");
  });
});

describe("RecordGrid in History", () => {
  it("hides every editing affordance when read only", async () => {
    stubGrid();
    renderWithProviders(
      <RecordGrid
        type="transaction"
        month="2025-06"
        readOnly
        defaultDate="2025-06-01"
        caption="History"
      />,
    );

    await waitFor(() => expect(screen.getByText("Groceries")).toBeTruthy());
    expect(screen.queryByTestId("add-record")).toBeNull();
    expect(screen.queryByTestId("delete-selected")).toBeNull();
    expect(screen.queryByTestId("edit-1")).toBeNull();
    expect(screen.queryByLabelText("Select row Groceries")).toBeNull();
  });
});
