/**
 * Test helpers: a stubbed API and a provider wrapper.
 *
 * Every component test renders through the real QueryClient and locale context,
 * so hooks, cache invalidation and translation are exercised rather than mocked
 * away. Only `fetch` is replaced.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/preact-query";
import { render, renderHook } from "@testing-library/preact";
import type { ComponentChildren } from "preact";
import { useState } from "preact/hooks";
import { vi } from "vitest";

import { LocaleContext } from "@/components/LocaleContext";
import type { Language } from "@/types/api";

export interface StubRoute {
  /** Matched against the request URL. */
  match: RegExp;
  /** Matched against the method when set, so GET and DELETE can differ. */
  method?: string;
  status?: number;
  data?: unknown;
  error?: { code: string; message: string } | null;
  meta?: unknown;
}

interface StubResponse {
  ok: boolean;
  status: number;
  headers: { get: (name: string) => string | null };
  json: () => Promise<unknown>;
  text: () => Promise<string>;
}

function stubResponse(body: unknown, status: number): StubResponse {
  const serialised = JSON.stringify(body);
  return {
    ok: status >= 200 && status < 300,
    status,
    headers: { get: () => "application/json" },
    json: () => Promise.resolve(body),
    text: () => Promise.resolve(serialised),
  };
}

/**
 * Install a fetch stub driven by *routes*, first match wins.
 *
 * Returns the mock so a test can assert which URLs were called. An unmatched URL
 * answers 404 with a `NOT_FOUND` envelope, which makes a missing stub obvious
 * instead of silently rendering an empty screen.
 */
export function stubApi(routes: StubRoute[]): ReturnType<typeof vi.fn> {
  const mock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const method = (init?.method ?? "GET").toUpperCase();
    for (const route of routes) {
      if (!route.match.test(url)) {
        continue;
      }
      if (route.method !== undefined && route.method.toUpperCase() !== method) {
        continue;
      }
      return stubResponse(
        {
          data: route.data ?? null,
          error: route.error ?? null,
          meta: route.meta ?? null,
        },
        route.status ?? 200,
      );
    }
    return stubResponse(
      { data: null, error: { code: "NOT_FOUND", message: `No stub for ${url}` }, meta: null },
      404,
    );
  });
  vi.stubGlobal("fetch", mock);
  return mock;
}

/** Render *ui* inside the providers a screen expects in production. */
export function renderWithProviders(
  ui: ComponentChildren,
  locale: Language = "en",
): ReturnType<typeof render> {
  return render(<Providers locale={locale}>{ui}</Providers>);
}

/**
 * Render a hook inside the same providers.
 *
 * The QueryClient is created once per render tree, not per render, or a mutation
 * would write into a cache the next render has already thrown away.
 */
export function renderHookWithProviders<Result>(
  hook: () => Result,
): ReturnType<typeof renderHook<Result, never>> {
  return renderHook(hook, { wrapper: Providers });
}

function Providers({
  children,
  locale = "en",
}: {
  children: ComponentChildren;
  locale?: Language;
}) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: { retry: false },
          mutations: { retry: false },
        },
      }),
  );
  return (
    <QueryClientProvider client={client}>
      <LocaleContext.Provider value={locale}>{children}</LocaleContext.Provider>
    </QueryClientProvider>
  );
}
