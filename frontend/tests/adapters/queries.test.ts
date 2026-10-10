import { describe, expect, it, vi } from "vitest";

import { allPages, createQueryClient, keys, shouldRetry } from "@/adapters/queries";
import { ApiError } from "@/ports/api";

describe("shouldRetry", () => {
  it("retries network and server failures up to three times", () => {
    const network = new ApiError(0, "NETWORK", "");
    expect(shouldRetry(0, network)).toBe(true);
    expect(shouldRetry(2, new ApiError(503, "INTERNAL", ""))).toBe(true);
    expect(shouldRetry(3, network)).toBe(false);
  });

  it("never retries client errors", () => {
    expect(shouldRetry(0, new ApiError(401, "UNAUTHORIZED", ""))).toBe(false);
    expect(shouldRetry(0, new ApiError(409, "DUPLICATE_NAME", ""))).toBe(false);
  });

  it("retries unknown failures", () => {
    expect(shouldRetry(0, new Error("boom"))).toBe(true);
  });
});

describe("createQueryClient", () => {
  it("refetches on focus and never polls", () => {
    const options = createQueryClient().getDefaultOptions().queries;
    expect(options?.refetchOnWindowFocus).toBe(true);
    expect(options?.refetchInterval).toBe(false);
  });
});

describe("keys", () => {
  it("separate history queries by month and filters", () => {
    expect(keys.monthTransactions("2026-08", { q: "x" })).toEqual([
      "history",
      "transactions",
      "2026-08",
      { q: "x" },
    ]);
  });
});

describe("query error hook", () => {
  it("receives the error and the failing query's key", async () => {
    const seen: unknown[] = [];
    const client = createQueryClient((error, key) => seen.push([error, key]));
    const failure = new Error("nope");
    await client
      .query({ queryKey: ["x"], queryFn: () => Promise.reject(failure), retry: false })
      .catch(() => undefined);
    expect(seen).toEqual([[failure, ["x"]]]);
  });
});

describe("allPages", () => {
  it("reads pages until it has every item", async () => {
    const items = [1, 2, 3, 4, 5];
    const fetchPage = vi.fn((page: number) =>
      Promise.resolve({ items: items.slice((page - 1) * 2, page * 2), page, size: 2, total: items.length }),
    );
    expect(await allPages(fetchPage)).toEqual(items);
    expect(fetchPage.mock.calls.map(([page]) => page)).toEqual([1, 2, 3]);
  });

  it("stops on an empty page even if the total says more", async () => {
    const fetchPage = vi.fn((page: number) => Promise.resolve({ items: page === 1 ? [1] : [], page, size: 2, total: 9 }));
    expect(await allPages(fetchPage)).toEqual([1]);
  });
});
