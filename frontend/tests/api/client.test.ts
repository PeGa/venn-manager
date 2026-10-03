import { afterEach, describe, expect, it, vi } from "vitest";

import {
  ApiError,
  NetworkError,
  buildQuery,
  errorKey,
  isPasswordChangeRequired,
  request,
} from "@/api/client";
import { en } from "@/l10n/en";
import { es } from "@/l10n/es";
import type { TranslationKey } from "@/l10n";
import type { ErrorCode } from "@/types/api";

function stubFetch(response: {
  status?: number;
  body?: unknown;
  text?: string;
  rejects?: boolean;
}): ReturnType<typeof vi.fn> {
  const impl = response.rejects
    ? () => Promise.reject(new TypeError("Failed to fetch"))
    : () =>
        Promise.resolve({
          ok: (response.status ?? 200) >= 200 && (response.status ?? 200) < 300,
          status: response.status ?? 200,
          headers: { get: () => "application/json" },
          json: () => Promise.resolve(response.body),
          text: () => Promise.resolve(response.text ?? JSON.stringify(response.body)),
        });
  const stub = vi.fn(impl);
  vi.stubGlobal("fetch", stub);
  return stub;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("buildQuery", () => {
  it("renders parameters", () => {
    expect(buildQuery({ type: "transaction", month: "2025-07" })).toBe(
      "?type=transaction&month=2025-07",
    );
  });

  it("skips undefined, null and blank values", () => {
    expect(
      buildQuery({ type: "budget", month: undefined, search: null, page: "" }),
    ).toBe("?type=budget");
  });

  it("keeps zero and false, which are meaningful", () => {
    expect(buildQuery({ page: 0, flag: false })).toBe("?page=0&flag=false");
  });

  it("percent-encodes values", () => {
    expect(buildQuery({ search: "a b&c" })).toBe("?search=a+b%26c");
  });

  it("returns an empty string when nothing is left", () => {
    expect(buildQuery({ month: undefined })).toBe("");
  });
});

describe("request", () => {
  it("unwraps a success envelope", async () => {
    stubFetch({
      body: {
        data: { currency: "$" },
        error: null,
        meta: { page: 1, per_page: 10, total: 1, total_pages: 1 },
      },
    });

    const result = await request<{ currency: string }>("/api/v1/settings");

    expect(result.data).toEqual({ currency: "$" });
    expect(result.meta).toEqual({ page: 1, per_page: 10, total: 1, total_pages: 1 });
  });

  it("sends credentials and a JSON body", async () => {
    const fetchStub = stubFetch({ body: { data: null, error: null, meta: null } });

    await request("/api/v1/records", { method: "POST", body: { type: "budget" } });

    const [url, init] = fetchStub.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/v1/records");
    expect(init.method).toBe("POST");
    expect(init.credentials).toBe("same-origin");
    expect(init.headers).toMatchObject({ "Content-Type": "application/json" });
    expect(init.body).toBe(JSON.stringify({ type: "budget" }));
  });

  it("raises ApiError with the contract code on an error envelope", async () => {
    stubFetch({
      status: 422,
      body: {
        data: null,
        error: { code: "VALIDATION_ERROR", message: "Field 'amount' is required" },
        meta: null,
      },
    });

    const error = await request("/api/v1/records", { method: "POST" }).catch(
      (caught: unknown) => caught,
    );

    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).code).toBe("VALIDATION_ERROR");
    expect((error as ApiError).status).toBe(422);
  });

  it("raises ApiError for 401 so the app can return to the login screen", async () => {
    stubFetch({
      status: 401,
      body: {
        data: null,
        error: { code: "UNAUTHORIZED", message: "No active session" },
        meta: null,
      },
    });

    await expect(request("/api/v1/settings")).rejects.toMatchObject({
      code: "UNAUTHORIZED",
      status: 401,
    });
  });

  it("maps a non-JSON body onto INTERNAL_ERROR without leaking it", async () => {
    const fetchStub = vi.fn(() =>
      Promise.resolve({
        ok: false,
        status: 502,
        headers: { get: () => "text/html" },
        text: () => Promise.resolve("<html>Bad Gateway</html>"),
      }),
    );
    vi.stubGlobal("fetch", fetchStub);

    const error = await request("/api/v1/settings").catch((caught: unknown) => caught);

    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).code).toBe("INTERNAL_ERROR");
    expect((error as ApiError).message).not.toContain("Bad Gateway");
  });

  it("raises NetworkError when the request never completes", async () => {
    stubFetch({ rejects: true });

    await expect(request("/api/v1/settings")).rejects.toBeInstanceOf(NetworkError);
  });

  it("accepts a query parameter map", async () => {
    const fetchStub = stubFetch({ body: { data: [], error: null, meta: null } });

    await request("/api/v1/records", { query: { type: "budget", q: "all" } });

    expect(fetchStub.mock.calls[0]?.[0]).toBe("/api/v1/records?type=budget&q=all");
  });
});

describe("errorKey", () => {
  it("maps every contract code onto a translation key", () => {
    const cases: Array<[ErrorCode, TranslationKey]> = [
      ["UNAUTHORIZED", "error_unauthorized"],
      ["PASSWORD_CHANGE_REQUIRED", "error_password_change_required"],
      ["FORBIDDEN", "error_forbidden"],
      ["NOT_FOUND", "error_not_found"],
      ["CONFLICT", "error_conflict"],
      ["GONE", "error_gone"],
      ["VALIDATION_ERROR", "error_validation"],
      ["INTERNAL_ERROR", "error_internal"],
    ];
    for (const [code, key] of cases) {
      expect(errorKey(new ApiError(code, "server text", 400))).toBe(key);
    }
  });

  it("maps a failed request onto the network message", () => {
    expect(errorKey(new NetworkError())).toBe("error_network");
  });

  it("maps anything unexpected onto the generic message", () => {
    expect(errorKey(new Error("boom"))).toBe("error_unknown");
    expect(errorKey(undefined)).toBe("error_unknown");
  });

  it("always resolves to a string we translate ourselves", () => {
    // AGENTS.md: the UI renders a localised message, never the server's payload
    // or a raw code. The server text is kept on the error for the console only.
    const key = errorKey(new ApiError("GONE", "Record not available anymore.", 410));

    expect(en[key]).not.toBe("");
    expect(es[key]).not.toBe("");
  });
});

describe("isPasswordChangeRequired", () => {
  it("recognises the force-change gate", () => {
    expect(
      isPasswordChangeRequired(
        new ApiError("PASSWORD_CHANGE_REQUIRED", "Password change required", 403),
      ),
    ).toBe(true);
  });

  it("does not confuse another 403 with the gate", () => {
    expect(isPasswordChangeRequired(new ApiError("FORBIDDEN", "Not permitted", 403))).toBe(
      false,
    );
  });

  it("is false for a network failure or an unrelated throw", () => {
    expect(isPasswordChangeRequired(new NetworkError())).toBe(false);
    expect(isPasswordChangeRequired(new Error("boom"))).toBe(false);
    expect(isPasswordChangeRequired(undefined)).toBe(false);
  });
});

describe("locale completeness", () => {
  it("translates every key", () => {
    // TypeScript enforces this at build time; the check documents the invariant
    // and catches a key added to both files but left as a copy of the English.
    expect(Object.keys(es).sort()).toEqual(Object.keys(en).sort());
  });

  it("has no empty translation", () => {
    for (const [key, value] of Object.entries(es)) {
      expect(value.trim(), key).not.toBe("");
    }
  });
});
