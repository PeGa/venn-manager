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

const row = (payee: string) => screen.findByRole("option", { name: new RegExp(payee) });

describe("Transactions · list", () => {
  it("shows payee, member, day, category and signed amount", async () => {
    renderApp(createFakeApi().api, "/transactions");
    expect(text(await row("Greenfield Market"))).toContain("Alex · Today");
    expect(text(await row("Greenfield Market"))).toContain("Groceries");
    expect(text(await row("Greenfield Market"))).toContain("−$84.12");
    expect(text(await row("Paycheck Northwind"))).toContain("Jordan · Yesterday");
    expect(text(await row("Paycheck Northwind"))).toContain("+$2,240.00");
  });

  it("marks rows of deleted categories and keeps them read-only", async () => {
    const { api, state } = createFakeApi();
    state.transactions[0]!.categoryDeleted = true;
    renderApp(api, "/transactions");
    const market = await row("Greenfield Market");
    expect(text(market)).toContain("Groceries (deleted)");
    expect(market.getAttribute("aria-disabled")).toBe("true");
    fireEvent.click(market);
    expect(market.getAttribute("aria-selected")).toBe("false");
  });
});

describe("Transactions · add bar", () => {
  it("adds a literal signed amount against the chosen category", async () => {
    const { api } = createFakeApi();
    renderApp(api, "/transactions");
    const add = await screen.findByRole("button", { name: "Add" });
    expect(add.hasAttribute("disabled")).toBe(true);
    fireEvent.input(screen.getByLabelText("Payee"), { target: { value: "Bakery" } });
    fireEvent.input(screen.getByLabelText("Amount"), { target: { value: "-12,5" } });
    fireEvent.click(screen.getByRole("button", { name: "Category: Groceries" }));
    fireEvent.click(add);
    await waitFor(() =>
      expect(api.createTransaction).toHaveBeenCalledWith({ payee: "Bakery", budgetId: "b-dining", amount: -1250 }),
    );
    await waitFor(() => expect(screen.getByLabelText<HTMLInputElement>("Payee").value).toBe(""));
    expect(screen.getByRole("button", { name: "Category: Dining out" })).toBeTruthy();
  });

  it("treats a bare number as money coming in and an empty payee as Untitled", async () => {
    const { api } = createFakeApi();
    renderApp(api, "/transactions");
    const amount = await screen.findByLabelText("Amount");
    fireEvent.input(amount, { target: { value: "25" } });
    fireEvent.keyDown(amount, { key: "Enter" });
    await waitFor(() =>
      expect(api.createTransaction).toHaveBeenCalledWith({ payee: "Untitled", budgetId: "b-groceries", amount: 2500 }),
    );
  });

  it("asks for a budget first when there is none", async () => {
    const { api, state } = createFakeApi();
    state.budgets = [];
    renderApp(api, "/transactions");
    expect(await screen.findByRole("link", { name: "Add a budget concept in Settings to start logging" })).toBeTruthy();
    expect(screen.queryByLabelText("Payee")).toBeNull();
  });
});

describe("Transactions · selection with a mouse", () => {
  it("selects, toggles and ranges, enabling the right actions", async () => {
    renderApp(createFakeApi().api, "/transactions");
    const edit = await screen.findByRole("button", { name: "Edit selected" });
    const remove = screen.getByRole("button", { name: "Remove selected" });
    expect(screen.getByText("Click a row to select · Ctrl/⌘ for several · Shift for a range")).toBeTruthy();
    fireEvent.click(await row("Greenfield Market"));
    expect(edit.hasAttribute("disabled")).toBe(false);
    fireEvent.click(await row("Kiez Bistro"), { shiftKey: true });
    expect(screen.getByText("4 selected")).toBeTruthy();
    expect(edit.hasAttribute("disabled")).toBe(true);
    expect(remove.hasAttribute("disabled")).toBe(false);
    fireEvent.click(await row("Corner Coffee"), { ctrlKey: true });
    expect(screen.getByText("3 selected")).toBeTruthy();
  });

  it("edits one row inline and saves only what changed", async () => {
    const { api } = createFakeApi();
    renderApp(api, "/transactions");
    fireEvent.click(await row("Kiez Bistro"));
    fireEvent.click(screen.getByRole("button", { name: "Edit selected" }));
    const bar = await screen.findByRole("form", { name: "Editing" });
    expect(within(bar).getByLabelText<HTMLInputElement>("Amount").value).toBe("-64");
    fireEvent.input(within(bar).getByLabelText("Amount"), { target: { value: "-70" } });
    fireEvent.click(within(bar).getByRole("button", { name: "Save" }));
    await waitFor(() => expect(api.updateTransaction).toHaveBeenCalledWith("t-bistro", { amount: -7000 }));
  });

  it("removes one row at once and several after confirming", async () => {
    const { api } = createFakeApi();
    renderApp(api, "/transactions");
    fireEvent.click(await row("Kiez Bistro"));
    fireEvent.click(screen.getByRole("button", { name: "Remove selected" }));
    await waitFor(() => expect(api.deleteTransaction).toHaveBeenCalledWith("t-bistro"));
    fireEvent.click(await row("Greenfield Market"));
    fireEvent.click(await row("Corner Coffee"), { metaKey: true });
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
    fireEvent.click(await row("Kiez Bistro"));
    const sheet = await screen.findByRole("dialog", { name: "Kiez Bistro" });
    fireEvent.click(within(sheet).getByRole("button", { name: "Remove" }));
    await waitFor(() => expect(api.deleteTransaction).toHaveBeenCalledWith("t-bistro"));
  });

  it("enters select mode on long press", async () => {
    renderApp(createFakeApi().api, "/transactions");
    const bistro = await row("Kiez Bistro");
    fireEvent.pointerDown(bistro);
    await new Promise((resolve) => setTimeout(resolve, 500));
    fireEvent.pointerUp(bistro);
    fireEvent.click(bistro);
    expect(await screen.findByText("1 selected")).toBeTruthy();
    fireEvent.click(await row("Corner Coffee"));
    expect(await screen.findByText("2 selected")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Done" }));
    await waitFor(() => expect(screen.queryByText("2 selected")).toBeNull());
  });
});
