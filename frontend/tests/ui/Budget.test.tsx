import { fireEvent, screen, waitFor, within } from "@solidjs/testing-library";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { createFakeApi } from "./fakeApi";
import { renderApp, text } from "./render";

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"], now: new Date("2026-09-28T10:00:00Z") });
});
afterEach(() => {
  vi.useRealTimers();
});

async function card(name: string) {
  return screen.findByRole("region", { name });
}

describe("Budget", () => {
  it("lists spending and income budgets with their period and note", async () => {
    renderApp(createFakeApi().api, "/budget");
    const groceries = await card("Groceries");
    expect(text(groceries)).toContain("SEP 1–30");
    expect(text(groceries)).toContain("$604 spent · $196 left");
    expect(within(groceries).getByRole<HTMLInputElement>("textbox", { name: "Groceries amount" }).value).toBe("-800");
    expect(text(await card("Paycheck"))).toContain("$2,240 received · $0 to go");
    expect(screen.queryByRole("region", { name: "Lisbon trip" })).toBeNull();
  });

  it("steps the amount literally and saves the absolute value", async () => {
    const { api } = createFakeApi();
    renderApp(api, "/budget");
    const groceries = await card("Groceries");
    fireEvent.click(within(groceries).getByRole("button", { name: "Increase by 50" }));
    expect(within(groceries).getByRole<HTMLInputElement>("textbox", { name: "Groceries amount" }).value).toBe("-750");
    expect(text(groceries)).toContain("$604 spent · $146 left");
    await waitFor(() => expect(api.updateBudget).toHaveBeenCalledWith("b-groceries", { amount: -75000 }));
  });

  it("saves a typed amount and reverts one that does not parse", async () => {
    const { api } = createFakeApi();
    renderApp(api, "/budget");
    const dining = await card("Dining out");
    const input = within(dining).getByRole<HTMLInputElement>("textbox", { name: "Dining out amount" });
    fireEvent.input(input, { target: { value: "-400.50" } });
    await waitFor(() => expect(api.updateBudget).toHaveBeenCalledWith("b-dining", { amount: -40050 }));
    fireEvent.input(input, { target: { value: "lots" } });
    fireEvent.blur(input);
    expect(input.value).toBe("-400.5");
  });

  it("moves a budget to Goals when Goal is ticked", async () => {
    const { api } = createFakeApi();
    renderApp(api, "/budget");
    const dining = await card("Dining out");
    fireEvent.click(within(dining).getByRole("checkbox", { name: "Goal" }));
    await waitFor(() => expect(api.updateBudget).toHaveBeenCalledWith("b-dining", { goal: true }));
    await waitFor(() => expect(screen.queryByRole("region", { name: "Dining out" })).toBeNull());
  });

  it("sets a schedule from the due chip", async () => {
    const { api } = createFakeApi();
    renderApp(api, "/budget");
    const groceries = await card("Groceries");
    fireEvent.click(within(groceries).getByRole("button", { name: "No due date" }));
    const dialog = await screen.findByRole("dialog", { name: "When is Groceries due?" });
    fireEvent.change(within(dialog).getByLabelText("Repeat"), { target: { value: "weekly" } });
    fireEvent.input(within(dialog).getByLabelText("First due date"), { target: { value: "2026-09-06" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Save" }));
    await waitFor(() => { expect(api.updateBudget).toHaveBeenCalledWith("b-groceries", {
        schedule: { repeat: "weekly", anchor: "2026-09-06" },
      }); },
    );
    expect(await within(groceries).findByRole("button", { name: "Weekly · Sundays" })).toBeTruthy();
  });

  it("requires a date unless the schedule is cleared", async () => {
    const { api } = createFakeApi();
    renderApp(api, "/budget");
    const groceries = await card("Groceries");
    fireEvent.click(within(groceries).getByRole("button", { name: "No due date" }));
    const dialog = await screen.findByRole("dialog", { name: "When is Groceries due?" });
    fireEvent.change(within(dialog).getByLabelText("Repeat"), { target: { value: "monthly" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Save" }));
    expect(await within(dialog).findByText("Pick a date")).toBeTruthy();
    expect(api.updateBudget).not.toHaveBeenCalled();
  });

  it("links to Settings to add concepts", async () => {
    renderApp(createFakeApi().api, "/budget");
    fireEvent.click(await screen.findByRole("link", { name: "+ Add budget concept in Settings" }));
    expect(await screen.findByRole("heading", { name: "Settings" })).toBeTruthy();
  });
});

describe("Goals", () => {
  it("lists goal budgets with goal wording", async () => {
    renderApp(createFakeApi().api, "/goals");
    const trip = await card("Lisbon trip");
    expect(text(trip)).toContain("$96 of $220 · $124 to go");
    expect(within(trip).getByRole<HTMLInputElement>("checkbox", { name: "Goal" }).checked).toBe(true);
  });

  it("explains how to add goals when there are none", async () => {
    const { api, state } = createFakeApi();
    state.budgets = state.budgets.filter((b) => !b.goal);
    renderApp(api, "/goals");
    expect(await screen.findByText("Tick Goal on a budget to track it here.")).toBeTruthy();
  });
});
