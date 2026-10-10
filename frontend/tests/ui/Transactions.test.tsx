import { fireEvent, screen, waitFor, within } from "@solidjs/testing-library";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { createFakeApi } from "./fakeApi";
import { renderApp, text } from "./render";

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"], now: new Date("2026-09-28T10:00:00Z") });
});
afterEach(() => {
  vi.useRealTimers();
  vi.mocked(window.matchMedia).mockImplementation(
    (query: string) =>
      ({
        matches: false,
        media: query,
        onchange: null,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        addListener: vi.fn(),
        removeListener: vi.fn(),
        dispatchEvent: vi.fn(),
      }),
  );
});

// Rows of the seeded ledger, found by their signed amount.
const MARKET = "−\\$84\\.12";
const COFFEE = "−\\$6\\.40";
const PAY = "\\+\\$2,240\\.00";
const BISTRO = "−\\$64\\.00";
const row = (amount: string) => screen.findByRole("option", { name: new RegExp(amount) });

describe("Transactions · list", () => {
  it("titles each row by its category, then member, day and signed amount", async () => {
    renderApp(createFakeApi().api, "/transactions");
    expect(text(await row(MARKET))).toBe("AGroceriesAlex · Today−$84.12");
    expect(text(await row(PAY))).toBe("JPaycheckJordan · Yesterday+$2,240.00");
  });

  it("marks rows of deleted categories and keeps them read-only", async () => {
    const { api, state } = createFakeApi();
    state.transactions[0]!.categoryDeleted = true;
    renderApp(api, "/transactions");
    const market = await row(MARKET);
    expect(text(market)).toContain("Groceries (deleted)");
    expect(market.getAttribute("aria-disabled")).toBe("true");
    fireEvent.click(market);
    expect(market.getAttribute("aria-selected")).toBe("false");
  });
});

describe("Transactions · add bar", () => {
  it("adds a literal signed amount against the category picked from the box", async () => {
    const { api } = createFakeApi();
    renderApp(api, "/transactions");
    const add = await screen.findByRole("button", { name: "Add" });
    expect(add.hasAttribute("disabled")).toBe(true);
    expect(screen.queryByLabelText("Payee")).toBeNull();
    fireEvent.input(screen.getByLabelText("Amount"), { target: { value: "-12,5" } });
    fireEvent.click(screen.getByRole("button", { name: "Category: Groceries" }));
    const box = screen.getByRole("group", { name: "Categories" });
    expect(within(box).getAllByRole("button").map((chip) => chip.textContent)).toEqual([
      "Groceries",
      "Dining out",
      "Paycheck",
      "Lisbon trip",
    ]);
    expect(within(box).getByRole("button", { name: "Groceries" }).getAttribute("aria-pressed")).toBe("true");
    fireEvent.click(within(box).getByRole("button", { name: "Dining out" }));
    expect(screen.queryByRole("group", { name: "Categories" })).toBeNull();
    fireEvent.click(add);
    await waitFor(() => expect(api.createTransaction).toHaveBeenCalledWith({ budgetId: "b-dining", amount: -1250 }));
    await waitFor(() => expect(screen.getByLabelText<HTMLInputElement>("Amount").value).toBe(""));
    expect(screen.getByRole("button", { name: "Category: Dining out" })).toBeTruthy();
  });

  it("closes the category box on Escape or a click outside without a change", async () => {
    renderApp(createFakeApi().api, "/transactions");
    const picker = await screen.findByRole("button", { name: "Category: Groceries" });
    fireEvent.click(picker);
    expect(picker.getAttribute("aria-expanded")).toBe("true");
    fireEvent.keyDown(screen.getByRole("group", { name: "Categories" }), { key: "Escape" });
    expect(screen.queryByRole("group", { name: "Categories" })).toBeNull();
    fireEvent.click(picker);
    fireEvent.pointerDown(document.body);
    expect(screen.queryByRole("group", { name: "Categories" })).toBeNull();
    expect(picker.getAttribute("aria-expanded")).toBe("false");
    expect(screen.getByRole("button", { name: "Category: Groceries" })).toBe(picker);
  });

  it("treats a bare number as money coming in", async () => {
    const { api } = createFakeApi();
    renderApp(api, "/transactions");
    const amount = await screen.findByLabelText("Amount");
    fireEvent.input(amount, { target: { value: "25" } });
    fireEvent.keyDown(amount, { key: "Enter" });
    await waitFor(() => expect(api.createTransaction).toHaveBeenCalledWith({ budgetId: "b-groceries", amount: 2500 }));
  });

  it("asks for a budget first when there is none", async () => {
    const { api, state } = createFakeApi();
    state.budgets = [];
    renderApp(api, "/transactions");
    expect(await screen.findByRole("link", { name: "Add a budget concept in Settings to start logging" })).toBeTruthy();
    expect(screen.queryByLabelText("Amount")).toBeNull();
  });
});

describe("Transactions · selection with a mouse", () => {
  it("selects, toggles and ranges, enabling the right actions", async () => {
    renderApp(createFakeApi().api, "/transactions");
    const edit = await screen.findByRole("button", { name: "Edit selected" });
    const remove = screen.getByRole("button", { name: "Remove selected" });
    expect(screen.getByText("Click a row to select · Ctrl/⌘ for several · Shift for a range")).toBeTruthy();
    fireEvent.click(await row(MARKET));
    expect(edit.hasAttribute("disabled")).toBe(false);
    fireEvent.click(await row(BISTRO), { shiftKey: true });
    expect(screen.getByText("4 selected")).toBeTruthy();
    expect(edit.hasAttribute("disabled")).toBe(true);
    expect(remove.hasAttribute("disabled")).toBe(false);
    fireEvent.click(await row(COFFEE), { ctrlKey: true });
    expect(screen.getByText("3 selected")).toBeTruthy();
  });

  it("edits one row inline and saves only what changed", async () => {
    const { api } = createFakeApi();
    renderApp(api, "/transactions");
    fireEvent.click(await row(BISTRO));
    fireEvent.click(screen.getByRole("button", { name: "Edit selected" }));
    const bar = await screen.findByRole("form", { name: "Editing" });
    expect(within(bar).getByLabelText<HTMLInputElement>("Amount").value).toBe("-64");
    fireEvent.input(within(bar).getByLabelText("Amount"), { target: { value: "-70" } });
    fireEvent.click(within(bar).getByRole("button", { name: "Category: Dining out" }));
    fireEvent.click(within(bar).getByRole("button", { name: "Groceries" }));
    fireEvent.click(within(bar).getByRole("button", { name: "Save" }));
    await waitFor(() =>
      expect(api.updateTransaction).toHaveBeenCalledWith("t-bistro", { amount: -7000, budgetId: "b-groceries" }),
    );
  });

  it("removes one row at once and several after confirming", async () => {
    const { api } = createFakeApi();
    renderApp(api, "/transactions");
    fireEvent.click(await row(BISTRO));
    fireEvent.click(screen.getByRole("button", { name: "Remove selected" }));
    await waitFor(() => expect(api.deleteTransaction).toHaveBeenCalledWith("t-bistro"));
    fireEvent.click(await row(MARKET));
    fireEvent.click(await row(COFFEE), { metaKey: true });
    fireEvent.click(screen.getByRole("button", { name: "Remove selected" }));
    const dialog = await screen.findByRole("dialog", { name: "Remove 2 transactions?" });
    fireEvent.click(within(dialog).getByRole("button", { name: "Remove" }));
    await waitFor(() => expect(api.bulkDeleteTransactions).toHaveBeenCalledWith(["t-market", "t-coffee"]));
  });
});

describe("Transactions · touch", () => {
  beforeEach(() => {
    vi.mocked(window.matchMedia).mockImplementation(
      (query: string) =>
        ({
          matches: query.includes("coarse"),
          media: query,
          onchange: null,
          addEventListener: vi.fn(),
          removeEventListener: vi.fn(),
          addListener: vi.fn(),
          removeListener: vi.fn(),
          dispatchEvent: vi.fn(),
        }),
    );
  });

  it("opens an action sheet on tap and removes from it", async () => {
    const { api } = createFakeApi();
    renderApp(api, "/transactions");
    fireEvent.click(await row(BISTRO));
    const sheet = await screen.findByRole("dialog", { name: "Dining out · −$64.00" });
    fireEvent.click(within(sheet).getByRole("button", { name: "Remove" }));
    await waitFor(() => expect(api.deleteTransaction).toHaveBeenCalledWith("t-bistro"));
  });

  it("edits amount and category in a sheet", async () => {
    const { api } = createFakeApi();
    renderApp(api, "/transactions");
    fireEvent.click(await row(BISTRO));
    fireEvent.click(within(await screen.findByRole("dialog", { name: "Dining out · −$64.00" })).getByRole("button", { name: "Edit" }));
    const sheet = await screen.findByRole("form", { name: "Editing" });
    fireEvent.click(within(sheet).getByRole("button", { name: "Category: Dining out" }));
    fireEvent.click(within(sheet).getByRole("button", { name: "Paycheck" }));
    fireEvent.click(within(sheet).getByRole("button", { name: "Save" }));
    await waitFor(() => expect(api.updateTransaction).toHaveBeenCalledWith("t-bistro", { budgetId: "b-paycheck" }));
  });

  it("enters select mode on long press", async () => {
    renderApp(createFakeApi().api, "/transactions");
    const bistro = await row(BISTRO);
    fireEvent.pointerDown(bistro);
    await new Promise((resolve) => setTimeout(resolve, 500));
    fireEvent.pointerUp(bistro);
    fireEvent.click(bistro);
    expect(await screen.findByText("1 selected")).toBeTruthy();
    fireEvent.click(await row(COFFEE));
    expect(await screen.findByText("2 selected")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Done" }));
    await waitFor(() => expect(screen.queryByText("2 selected")).toBeNull());
  });
});
