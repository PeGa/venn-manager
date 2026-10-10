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

describe("Overview", () => {
  it("leads with the month-end forecast and its formula", async () => {
    renderApp(createFakeApi().api);
    const hero = await screen.findByRole("region", { name: "Month-end forecast" });
    expect(text(hero)).toContain("$14,385.88");
    expect(text(hero)).toContain("Start-of-month cash$12,900.00");
    expect(text(hero)).toContain("Planned (still to move)−$599.60");
    expect(text(hero)).toContain("Logged transactions (4)+$2,085.48");
    expect(text(hero)).toContain("$12,900.00 − $599.60 + $2,085.48 = $14,385.88");
    expect(text(hero)).toContain("What's this?");
    expect(screen.queryByText(/Left to spend/)).toBeNull();
  });

  it("explains the forecast with every transaction and every budget still to move", async () => {
    const { api, state } = createFakeApi();
    state.transactions[3]!.categoryDeleted = true;
    renderApp(api);
    const hero = await screen.findByRole("region", { name: "Month-end forecast" });
    fireEvent.click(within(hero).getByRole("button", { name: "Explain" }));
    const dialog = await screen.findByRole("dialog", { name: "How the forecast adds up" });
    await waitFor(() => expect(text(dialog)).toContain("Lisbon trip"));
    const section = (name: string) => within(dialog).getByRole("region", { name });
    expect(text(section("Start-of-month cash"))).toContain("$12,900.00");
    const logged = section("Logged transactions (4)");
    expect(text(logged)).toContain("+$2,085.48");
    expect(within(logged).getAllByRole("listitem").map(text)).toEqual([
      "GroceriesAlex · Today−$84.12",
      "Dining outJordan · Today−$6.40",
      "PaycheckJordan · Yesterday+$2,240.00",
    ]);
    const planned = section("Planned (still to move)");
    expect(text(planned)).toContain("−$599.60");
    expect(within(planned).getAllByRole("listitem").map(text)).toEqual([
      "Groceries−$196.00",
      "Dining out−$279.60",
      "Lisbon trip−$124.00",
    ]);
    expect(text(dialog)).toContain("Forecast$14,385.88");
    expect(api.transactions).toHaveBeenCalledWith({ page: 1, size: 200 });
    fireEvent.click(within(dialog).getByRole("button", { name: "Close" }));
    await waitFor(() => expect(screen.queryByRole("dialog", { name: "How the forecast adds up" })).toBeNull());
  });

  it("says when a section of the explanation is empty", async () => {
    const { api, state } = createFakeApi();
    state.transactions = [];
    renderApp(api);
    fireEvent.click(await screen.findByRole("button", { name: "Explain" }));
    const dialog = await screen.findByRole("dialog", { name: "How the forecast adds up" });
    await waitFor(() => expect(text(dialog)).toContain("None this month."));
  });

  it("lists what is coming up", async () => {
    renderApp(createFakeApi().api);
    const card = await screen.findByRole("region", { name: "Coming up" });
    expect(text(card)).toContain("Rent");
    expect(text(card)).toContain("Due in 2 days");
    expect(text(card)).toContain("$0 of $2,150");
  });

  it("words recent activity and navigates to its target", async () => {
    renderApp(createFakeApi().api);
    const card = await screen.findByRole("region", { name: "Recent activity" });
    const entry = within(card).getByRole("button", { name: /Jordan set the Dining out budget to −\$350/ });
    expect(text(entry)).toContain("Yesterday · Budget");
    expect(text(within(card).getByRole("button", { name: /Alex added −\$84\.12 to Groceries/ }))).toContain(
      "Just now · Transactions",
    );
    fireEvent.click(entry);
    expect(await screen.findByRole("heading", { name: "Budget" })).toBeTruthy();
  });

  it("does not offer navigation for entries without a target", async () => {
    const { api, state } = createFakeApi();
    state.activity = [
      {
        id: "a9",
        actorId: "m-alex",
        action: "tx.bulkDelete",
        params: { count: 2 },
        at: "2026-09-26T10:00:00Z",
        target: { type: "none" },
      },
    ];
    renderApp(api);
    const card = await screen.findByRole("region", { name: "Recent activity" });
    expect(within(card).getByText(/removed 2 transactions/)).toBeTruthy();
    expect(within(card).queryByRole("button")).toBeNull();
  });
});

describe("forecast formula", () => {
  it("never wraps between an operator and its number", async () => {
    const { formula } = await import("@/ui/screens/Overview");
    const text = formula({ startCash: 0, planned: -320948, transactionsNet: 214948, transactionCount: 3, total: -106000 }, "$");
    expect(text).toBe("$0.00 −\u00a0$3,209.48 +\u00a0$2,149.48 =\u00a0−$1,060.00");
  });
});
