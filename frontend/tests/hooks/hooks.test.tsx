/**
 * Hook and API-layer tests.
 *
 * These pin the wire contract from the client side: the URL, the method, the
 * query parameters and the body each hook produces. If an endpoint's shape in
 * API_SURFACE.md changes, the assertion here breaks first.
 */
import { act, renderHook, waitFor } from "@testing-library/preact";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useConcepts, useAllConcepts, useConceptsByFlow, useCreateConcept, useRenameConcept, useDeleteConcept, useBulkDeleteConcepts } from "@/hooks/useConcepts";
import { useProjections, useMonthState, useSwitchMonth } from "@/hooks/useProjections";
import { selectedIds, useRecords, useCreateRecord, useUpdateRecord, useDeleteRecord, useBulkDeleteRecords } from "@/hooks/useRecords";
import { useChangePassword, useLogin, useLogout, useSession } from "@/hooks/useSession";
import { useSettings, useUpdateSettings } from "@/hooks/useSettings";
import { useTheme } from "@/hooks/useTheme";
import { useCreateUser, useDeleteUser, useUpdateUser, useUsers } from "@/hooks/useUsers";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import { renderHookWithProviders, stubApi } from "../helpers";
import { setMediaMatch } from "../setup";
import type { MoneyRecord } from "@/types/api";

interface Call {
  url: string;
  method: string;
  body?: string;
}

function calls(mock: ReturnType<typeof vi.fn>): Call[] {
  return mock.mock.calls.map(([url, init]) => ({
    url: String(url),
    method: ((init as RequestInit | undefined)?.method ?? "GET").toUpperCase(),
    body: (init as RequestInit | undefined)?.body as string | undefined,
  }));
}

function find(mock: ReturnType<typeof vi.fn>, fragment: string, method = "GET"): Call | undefined {
  return calls(mock).find((call) => call.url.includes(fragment) && call.method === method);
}

const SESSION = {
  user: { id: 1, username: "admin", real_name: "Administrator", is_admin: true },
  must_change_password: false,
};

const SETTINGS = {
  currency: "$",
  language: "en",
  theme: "dark",
  last_acknowledged_month: "2025-07",
  username: "admin",
  real_name: "Administrator",
};

const RECORD: MoneyRecord = {
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
};

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("session hooks", () => {
  it("reads the session", async () => {
    const mock = stubApi([{ match: /\/auth\/session/, data: SESSION }]);

    const { result } = renderHookWithProviders(() => useSession());
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.data.user.username).toBe("admin");
    expect(find(mock, "/auth/session")).toBeTruthy();
  });

  it("signs in and caches the session", async () => {
    const mock = stubApi([{ match: /\/auth\/login/, method: "POST", data: SESSION }]);

    const { result } = renderHookWithProviders(() => useLogin());
    act(() => result.current.mutate({ username: "admin", password: "admin" }));
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    const call = find(mock, "/auth/login", "POST");
    expect(JSON.parse(call?.body ?? "{}")).toEqual({
      username: "admin",
      password: "admin",
    });
  });

  it("signs out with POST", async () => {
    const mock = stubApi([{ match: /\/auth\/logout/, method: "POST" }]);

    const { result } = renderHookWithProviders(() => useLogout());
    act(() => result.current.mutate());
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(find(mock, "/auth/logout", "POST")).toBeTruthy();
  });

  it("changes the password with both halves of the body", async () => {
    const mock = stubApi([{ match: /\/auth\/password/, method: "POST" }]);

    const { result } = renderHookWithProviders(() => useChangePassword());
    act(() =>
      result.current.mutate({ currentPassword: "old-pass", newPassword: "new-pass" }),
    );
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(JSON.parse(find(mock, "/auth/password", "POST")?.body ?? "{}")).toEqual({
      current_password: "old-pass",
      new_password: "new-pass",
    });
  });
});

describe("settings hooks", () => {
  it("reads merged settings", async () => {
    stubApi([{ match: /\/settings$/, data: SETTINGS }]);

    const { result } = renderHookWithProviders(() => useSettings(true));
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.data.theme).toBe("dark");
  });

  it("does not fetch while disabled", () => {
    const mock = stubApi([{ match: /\/settings$/, data: SETTINGS }]);

    const { result } = renderHookWithProviders(() => useSettings(false));

    expect(result.current.fetchStatus).toBe("idle");
    expect(calls(mock)).toEqual([]);
  });

  it("patches settings with PATCH", async () => {
    const mock = stubApi([
      { match: /\/settings$/, method: "PATCH", data: { currency: "€" } },
    ]);

    const { result } = renderHookWithProviders(() => useUpdateSettings());
    act(() => result.current.mutate({ currency: "€" }));
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    const call = find(mock, "/settings", "PATCH");
    expect(JSON.parse(call?.body ?? "{}")).toEqual({ currency: "€" });
  });
});

describe("concept hooks", () => {
  it("asks for the live list by default", async () => {
    const mock = stubApi([{ match: /\/settings\/concepts/, data: [] }]);

    const { result } = renderHookWithProviders(() => useConcepts());
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(find(mock, "include_deleted=false")?.url).toContain("/settings/concepts");
  });

  it("asks for deleted concepts when the grid toggle is on", async () => {
    const mock = stubApi([{ match: /\/settings\/concepts/, data: [] }]);

    const { result } = renderHookWithProviders(() => useAllConcepts());
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(find(mock, "include_deleted=true")).toBeTruthy();
  });

  it("filters pickers by flow", async () => {
    const mock = stubApi([{ match: /\/settings\/concepts/, data: [] }]);

    const { result } = renderHookWithProviders(() => useConceptsByFlow("in"));
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(find(mock, "flow=in")).toBeTruthy();
  });

  it("creates, renames and deletes", async () => {
    const mock = stubApi([
      { match: /\/settings\/concepts\/\d+$/, method: "PATCH", data: {} },
      { match: /\/settings\/concepts\/\d+$/, method: "DELETE" },
      { match: /\/settings\/concepts$/, method: "POST", status: 201, data: {} },
    ]);

    const create = renderHookWithProviders(() => useCreateConcept());
    act(() => create.result.current.mutate({ name: "Rent", flow: "out" }));
    await waitFor(() => expect(create.result.current.isSuccess).toBe(true));
    expect(JSON.parse(find(mock, "/settings/concepts", "POST")?.body ?? "{}")).toEqual({
      name: "Rent",
      flow: "out",
    });

    const rename = renderHookWithProviders(() => useRenameConcept());
    act(() => rename.result.current.mutate({ id: 7, name: "Monthly Rent" }));
    await waitFor(() => expect(rename.result.current.isSuccess).toBe(true));
    expect(find(mock, "/settings/concepts/7", "PATCH")).toBeTruthy();
    expect(JSON.parse(find(mock, "/settings/concepts/7", "PATCH")?.body ?? "{}")).toEqual({
      name: "Monthly Rent",
    });

    const remove = renderHookWithProviders(() => useDeleteConcept());
    act(() => remove.result.current.mutate(7));
    await waitFor(() => expect(remove.result.current.isSuccess).toBe(true));
    expect(find(mock, "/settings/concepts/7", "DELETE")).toBeTruthy();
  });

  it("bulk deletes with a comma-separated id list", async () => {
    const mock = stubApi([
      { match: /\/settings\/concepts\?ids=/, method: "DELETE", data: { deleted: 2 } },
    ]);

    const { result } = renderHookWithProviders(() => useBulkDeleteConcepts());
    act(() => result.current.mutate([3, 4]));
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(find(mock, "ids=3%2C4", "DELETE") ?? find(mock, "ids=3,4", "DELETE")).toBeTruthy();
  });
});

describe("record hooks", () => {
  it("sends type, month, page, q and search", async () => {
    const mock = stubApi([
      { match: /\/records/, data: [RECORD], meta: { page: 2, per_page: 20, total: 21, total_pages: 2 } },
    ]);

    const { result } = renderHookWithProviders(() =>
      useRecords({ type: "transaction", month: "2025-07", page: 2, size: 20, search: "gro" }),
    );
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    const url = find(mock, "/records")?.url ?? "";
    expect(url).toContain("type=transaction");
    expect(url).toContain("month=2025-07");
    expect(url).toContain("page=2");
    expect(url).toContain("q=20");
    expect(url).toContain("search=gro");
    expect(result.current.data?.meta?.total_pages).toBe(2);
  });

  it("omits the month for budgets", async () => {
    const mock = stubApi([{ match: /\/records/, data: [], meta: null }]);

    const { result } = renderHookWithProviders(() =>
      useRecords({ type: "budget", page: 1, size: "all", search: "" }),
    );
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    const url = find(mock, "/records")?.url ?? "";
    expect(url).not.toContain("month=");
    expect(url).toContain("q=all");
  });

  it("creates a record", async () => {
    const mock = stubApi([
      { match: /\/records/, method: "POST", status: 201, data: RECORD },
    ]);

    const { result } = renderHookWithProviders(() => useCreateRecord());
    act(() =>
      result.current.mutate({
        type: "transaction",
        date: "2025-07-15",
        concept_id: 3,
        amount: "45.50",
      }),
    );
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(JSON.parse(find(mock, "/records", "POST")?.body ?? "{}")).toEqual({
      type: "transaction",
      date: "2025-07-15",
      concept_id: 3,
      amount: "45.50",
    });
  });

  it("patches a record with type as a query parameter", async () => {
    const mock = stubApi([
      { match: /\/records\/\d+\?type=/, method: "PATCH", data: RECORD },
    ]);

    const { result } = renderHookWithProviders(() => useUpdateRecord());
    act(() =>
      result.current.mutate({ id: 1, type: "transaction", patch: { amount: "52.00" } }),
    );
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    const call = find(mock, "/records/1", "PATCH");
    expect(call?.url).toContain("type=transaction");
    expect(JSON.parse(call?.body ?? "{}")).toEqual({ amount: "52.00" });
  });

  it("deletes one record and many", async () => {
    const mock = stubApi([
      { match: /\/records\?type=.*ids=/, method: "DELETE", data: { deleted: 2 } },
      { match: /\/records\/\d+\?type=/, method: "DELETE" },
    ]);

    const one = renderHookWithProviders(() => useDeleteRecord());
    act(() => one.result.current.mutate({ id: 9, type: "budget" }));
    await waitFor(() => expect(one.result.current.isSuccess).toBe(true));
    expect(find(mock, "/records/9", "DELETE")?.url).toContain("type=budget");

    const many = renderHookWithProviders(() => useBulkDeleteRecords());
    act(() => many.result.current.mutate({ ids: [1, 2], type: "transaction" }));
    await waitFor(() => expect(many.result.current.isSuccess).toBe(true));
    expect(find(mock, "ids=1%2C2", "DELETE") ?? find(mock, "ids=1,2", "DELETE")).toBeTruthy();
  });

  it("narrows a page to the selected ids", () => {
    const rows = [RECORD, { ...RECORD, id: 2 }, { ...RECORD, id: 3 }];

    expect(selectedIds(rows, new Set([1, 3]))).toEqual([1, 3]);
    expect(selectedIds(rows, new Set())).toEqual([]);
    // An id from another page is not in `rows`, so it cannot be submitted.
    expect(selectedIds(rows, new Set([99]))).toEqual([]);
  });
});

describe("projection and month hooks", () => {
  it("requests the month it is given", async () => {
    const mock = stubApi([
      {
        match: /\/projections/,
        data: {
          spend_projection: 1250,
          earn_projection: 3000,
          savings_projection: 1750,
          actual_spend: 830.5,
          actual_earn: 3000,
        },
      },
    ]);

    const { result } = renderHookWithProviders(() => useProjections("2025-07"));
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(find(mock, "month=2025-07")).toBeTruthy();
    expect(result.current.data?.data.savings_projection).toBe(1750);
  });

  it("reads the month state", async () => {
    stubApi([
      {
        match: /\/current-month$/,
        data: {
          current_month: "2025-08",
          last_acknowledged_month: "2025-07",
          needs_switch: true,
          earliest_month: "2025-03",
        },
      },
    ]);

    const { result } = renderHookWithProviders(() => useMonthState());
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.data.needs_switch).toBe(true);
  });

  it("switches with POST", async () => {
    const mock = stubApi([
      {
        match: /\/current-month\/switch$/,
        method: "POST",
        data: {
          current_month: "2025-08",
          last_acknowledged_month: "2025-08",
          needs_switch: false,
          earliest_month: "2025-03",
        },
      },
    ]);

    const { result } = renderHookWithProviders(() => useSwitchMonth());
    act(() => result.current.mutate());
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(find(mock, "/current-month/switch", "POST")).toBeTruthy();
  });
});

describe("user management hooks", () => {
  it("lists, creates, updates and deletes users", async () => {
    const mock = stubApi([
      { match: /\/settings\/users\/\d+$/, method: "PATCH", data: {} },
      { match: /\/settings\/users\/\d+$/, method: "DELETE" },
      { match: /\/settings\/users$/, method: "POST", status: 201, data: {} },
      { match: /\/settings\/users$/, data: [SESSION.user] },
    ]);

    const list = renderHookWithProviders(() => useUsers(true));
    await waitFor(() => expect(list.result.current.isSuccess).toBe(true));
    expect(list.result.current.data?.data[0]?.username).toBe("admin");

    const create = renderHookWithProviders(() => useCreateUser());
    act(() =>
      create.result.current.mutate({
        username: "bob",
        real_name: "Bob",
        password: "a-password",
        is_admin: false,
      }),
    );
    await waitFor(() => expect(create.result.current.isSuccess).toBe(true));
    expect(find(mock, "/settings/users", "POST")).toBeTruthy();

    const update = renderHookWithProviders(() => useUpdateUser());
    act(() => update.result.current.mutate({ id: 2, patch: { is_admin: true } }));
    await waitFor(() => expect(update.result.current.isSuccess).toBe(true));
    expect(JSON.parse(find(mock, "/settings/users/2", "PATCH")?.body ?? "{}")).toEqual({
      is_admin: true,
    });

    const remove = renderHookWithProviders(() => useDeleteUser());
    act(() => remove.result.current.mutate(2));
    await waitFor(() => expect(remove.result.current.isSuccess).toBe(true));
    expect(find(mock, "/settings/users/2", "DELETE")).toBeTruthy();
  });
});

describe("useTheme", () => {
  afterEach(() => {
    delete document.documentElement.dataset.theme;
  });

  it("writes an explicit theme to the document", () => {
    renderHook(() => useTheme("dark"));

    expect(document.documentElement.dataset.theme).toBe("dark");
  });

  it("writes light for the light setting", () => {
    renderHook(() => useTheme("light"));

    expect(document.documentElement.dataset.theme).toBe("light");
  });

  it("resolves system against the OS preference", () => {
    setMediaMatch("(prefers-color-scheme: dark)", true);

    renderHook(() => useTheme("system"));

    expect(document.documentElement.dataset.theme).toBe("dark");
    setMediaMatch("(prefers-color-scheme: dark)", false);
  });

  it("resolves system to light when the OS prefers light", () => {
    renderHook(() => useTheme("system"));

    expect(document.documentElement.dataset.theme).toBe("light");
  });
});

describe("useDebouncedValue", () => {
  it("settles on the latest value after the delay", async () => {
    let value = "a";
    const { result, rerender } = renderHookWithProviders(() =>
      useDebouncedValue(value, 20),
    );
    expect(result.current).toBe("a");

    value = "ab";
    rerender();
    value = "abc";
    rerender();

    await waitFor(() => expect(result.current).toBe("abc"));
  });
});
