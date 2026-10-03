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

const month = (name: string) => screen.findByRole("region", { name });

describe("History", () => {
  it("groups past months newest first with their totals", async () => {
    renderApp(createFakeApi().api, "/history");
    const august = await month("August 2026");
    expect(text(august)).toContain("3 transactions · read-only");
    expect(text(august)).toContain("Spent$300");
    expect(text(august)).toContain("Earned$2,240");
    expect(text(await month("July 2026"))).toContain("1 transaction · read-only");
    const names = screen.getAllByRole("region").map((region) => region.getAttribute("aria-label"));
    expect(names.indexOf("August 2026")).toBeLessThan(names.indexOf("July 2026"));
  });

  it("lists each month's rows, marking deleted categories", async () => {
    renderApp(createFakeApi().api, "/history");
    const august = await month("August 2026");
    expect(await within(august).findByText("Cinema")).toBeTruthy();
    expect(text(august)).toContain("Old fun (deleted)");
    expect(within(august).queryByRole("option")).toBeNull();
  });

  it("filters on the server and shows partial counts", async () => {
    const { api } = createFakeApi();
    renderApp(api, "/history");
    await month("August 2026");
    fireEvent.input(screen.getByLabelText("Search payee, category or member"), { target: { value: "market" } });
    await waitFor(() => expect(api.historyMonths).toHaveBeenLastCalledWith(expect.objectContaining({ q: "market" })));
    expect(text(await month("August 2026"))).toContain("1 of 3 transactions");
    await waitFor(() => expect(screen.queryByRole("region", { name: "July 2026" })).toBeNull());
  });

  it("filters by member and category chips and clears everything", async () => {
    const { api } = createFakeApi();
    renderApp(api, "/history");
    await month("August 2026");
    const members = screen.getByRole("group", { name: "Member" });
    fireEvent.click(within(members).getByRole("button", { name: "Jordan" }));
    await waitFor(() => expect(api.historyMonths).toHaveBeenLastCalledWith(expect.objectContaining({ memberId: "m-jordan" })));
    const categories = screen.getByRole("group", { name: "Category" });
    fireEvent.click(within(categories).getByRole("button", { name: "Old fun (deleted)" }));
    await waitFor(() => expect(api.historyMonths).toHaveBeenLastCalledWith(expect.objectContaining({ budgetId: "b-old" })));
    fireEvent.click(screen.getByRole("button", { name: "Clear" }));
    await waitFor(() => expect(api.historyMonths).toHaveBeenLastCalledWith({ page: 1, size: 12 }));
  });

  it("shows the spending breakdown of a month", async () => {
    renderApp(createFakeApi().api, "/history");
    const august = await month("August 2026");
    fireEvent.click(within(august).getByRole("button", { name: "Details…" }));
    const dialog = await screen.findByRole("dialog", { name: "August 2026" });
    expect(text(dialog)).toContain("Spent $300 · Earned $2,240");
    expect(text(dialog)).toContain("Groceries$21271%");
    expect(text(dialog)).toContain("Dining out$8829%");
    fireEvent.click(within(dialog).getByRole("button", { name: "Close" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  });

  it("says when nothing matches and when there is no history yet", async () => {
    const { api } = createFakeApi();
    api.historyMonths.mockResolvedValue({ items: [], page: 1, size: 12, total: 0 });
    renderApp(api, "/history");
    expect(await screen.findByText("Nothing here yet. Months move here when they end.")).toBeTruthy();
    fireEvent.input(screen.getByLabelText("Search payee, category or member"), { target: { value: "zzz" } });
    expect(await screen.findByText("No transactions match these filters.")).toBeTruthy();
  });
});
