import { fireEvent, screen, within } from "@solidjs/testing-library";
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
  it("shows what is left to spend", async () => {
    renderApp(createFakeApi().api);
    const hero = await screen.findByRole("region", { name: "Left to spend this month" });
    expect(text(hero)).toContain("$476");
    expect(text(hero)).toContain("$674 of $1,150 budgeted · all members combined");
  });

  it("explains the forecast with its formula", async () => {
    renderApp(createFakeApi().api);
    const card = await screen.findByRole("region", { name: "Month-end forecast" });
    expect(text(card)).toContain("Start-of-month cash$12,900.00");
    expect(text(card)).toContain("Planned (still to move)−$285.20");
    expect(text(card)).toContain("Logged transactions (4)+$2,085.48");
    expect(text(card)).toContain("$12,900.00 − $285.20 + $2,085.48 = $14,700.28");
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
    expect(text(within(card).getByRole("button", { name: /Alex added “Greenfield Market”/ }))).toContain(
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
