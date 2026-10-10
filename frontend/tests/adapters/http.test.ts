import { describe, expect, it, vi } from "vitest";

import { createHttpApi } from "@/adapters/http";
import { ApiError } from "@/ports/api";

interface Call {
  url: string;
  init: RequestInit;
}

function fakeFetch(status: number, body: unknown, headers: Record<string, string> = {}) {
  const calls: Call[] = [];
  const fetcher = vi.fn((url: string, init: RequestInit = {}) => {
    calls.push({ url, init });
    const text = body === undefined ? "" : JSON.stringify(body);
    return Promise.resolve(new Response(status === 204 ? null : text, { status, headers }));
  });
  return { fetcher, calls };
}

describe("http adapter", () => {
  it("sends JSON with the session cookie to /api/v1", async () => {
    const { fetcher, calls } = fakeFetch(201, { id: "b1" });
    const api = createHttpApi({ fetcher });
    await api.createBudget("Groceries");
    expect(calls[0]?.url).toBe("/api/v1/budgets");
    expect(calls[0]?.init.method).toBe("POST");
    expect(calls[0]?.init.credentials).toBe("same-origin");
    expect(new Headers(calls[0]?.init.headers).get("Content-Type")).toBe("application/json");
    expect(calls[0]?.init.body).toBe(JSON.stringify({ name: "Groceries" }));
  });

  it("sends a JSON content type even on bodiless posts", async () => {
    const { fetcher, calls } = fakeFetch(204, undefined);
    await createHttpApi({ fetcher }).logout();
    expect(new Headers(calls[0]?.init.headers).get("Content-Type")).toBe("application/json");
  });

  it("returns nothing for 204 responses", async () => {
    const { fetcher } = fakeFetch(204, undefined);
    await expect(createHttpApi({ fetcher }).deleteBudget("b1")).resolves.toBeUndefined();
  });

  it("encodes paging and filters, skipping empty ones", async () => {
    const { fetcher, calls } = fakeFetch(200, { items: [], page: 2, size: 12, total: 0 });
    const api = createHttpApi({ fetcher });
    await api.historyMonths({ page: 2, size: 12, q: "café & co", memberId: "" });
    expect(calls[0]?.url).toBe("/api/v1/history/months?page=2&size=12&q=caf%C3%A9+%26+co");
    await api.historyTransactions("2026-08");
    expect(calls[1]?.url).toBe("/api/v1/history/months/2026-08/transactions");
  });

  it("sends null to clear a schedule", async () => {
    const { fetcher, calls } = fakeFetch(200, {});
    await createHttpApi({ fetcher }).updateBudget("b1", { schedule: null });
    expect(calls[0]?.init.method).toBe("PATCH");
    expect(calls[0]?.init.body).toBe('{"schedule":null}');
  });

  it("turns contract errors into ApiError", async () => {
    const { fetcher } = fakeFetch(409, {
      code: "DUPLICATE_NAME",
      message: "Budget name already used",
      field: "name",
    });
    const error = await createHttpApi({ fetcher }).createBudget("Rent").catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ status: 409, code: "DUPLICATE_NAME", field: "name" });
  });

  it("reports unexpected bodies as INTERNAL", async () => {
    const fetcher = vi.fn(() => Promise.resolve(new Response("<html>", { status: 502 })));
    const error = await createHttpApi({ fetcher }).overview().catch((e: unknown) => e);
    expect(error).toMatchObject({ status: 502, code: "INTERNAL" });
  });

  it("reports network failures as NETWORK", async () => {
    const fetcher = vi.fn(() => Promise.reject(new TypeError("Failed to fetch")));
    const error = await createHttpApi({ fetcher }).overview().catch((e: unknown) => e);
    expect(error).toMatchObject({ status: 0, code: "NETWORK" });
  });

  it("reports whether the backend was reachable", async () => {
    const onReachable = vi.fn();
    const down = vi.fn(() => Promise.reject(new TypeError("offline")));
    await createHttpApi({ fetcher: down, onReachable }).overview().catch(() => undefined);
    expect(onReachable).toHaveBeenLastCalledWith(false);
    const { fetcher } = fakeFetch(200, {});
    await createHttpApi({ fetcher, onReachable }).overview();
    expect(onReachable).toHaveBeenLastCalledWith(true);
  });

  it("reports every revision it sees", async () => {
    const { fetcher } = fakeFetch(200, {}, { "X-Ledger-Rev": "41" });
    const onRevision = vi.fn();
    await createHttpApi({ fetcher, onRevision }).household();
    expect(onRevision).toHaveBeenCalledWith(41);
  });

  it("maps every endpoint to its contract path", async () => {
    const { fetcher, calls } = fakeFetch(200, {});
    const api = createHttpApi({ fetcher });
    await api.login("admin", "pw");
    await api.session();
    await api.changePassword("a", "b");
    await api.updateMe({ theme: "dark" });
    await api.updateHousehold({ name: "Casa" });
    await api.createMember({ username: "j", realName: "J", password: "12345678", isAdmin: false });
    await api.updateMember("m1", { isAdmin: true });
    await api.removeMember("m1");
    await api.budgets();
    await api.transactions({ size: 200 });
    await api.createTransaction({ budgetId: "b1", amount: -1 });
    await api.updateTransaction("t1", { amount: -2 });
    await api.deleteTransaction("t1");
    await api.bulkDeleteTransactions(["t1", "t2"]);
    await api.upcoming();
    await api.activity({ page: 1, size: 5 });
    await api.balance();
    await api.historyBreakdown("2026-08", { budgetId: "b1" });
    await api.historyFacets();
    expect(calls.map((c) => `${c.init.method ?? "GET"} ${c.url}`)).toEqual([
      "POST /api/v1/auth/login",
      "GET /api/v1/auth/session",
      "POST /api/v1/auth/password",
      "PATCH /api/v1/me",
      "PATCH /api/v1/household",
      "POST /api/v1/members",
      "PATCH /api/v1/members/m1",
      "DELETE /api/v1/members/m1",
      "GET /api/v1/budgets",
      "GET /api/v1/transactions?size=200",
      "POST /api/v1/transactions",
      "PATCH /api/v1/transactions/t1",
      "DELETE /api/v1/transactions/t1",
      "POST /api/v1/transactions/bulk-delete",
      "GET /api/v1/upcoming",
      "GET /api/v1/activity?page=1&size=5",
      "GET /api/v1/balance",
      "GET /api/v1/history/months/2026-08/breakdown?budgetId=b1",
      "GET /api/v1/history/facets",
    ]);
  });
});
