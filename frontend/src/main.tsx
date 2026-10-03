/**
 * Browser entry point.
 *
 * One QueryClient for the whole app, configured with the cache and retry policy
 * AGENTS.md asks for: no refetch storm on re-render, and automatic retry of
 * network failures with at most three attempts.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/preact-query";
import { render } from "preact";

import { App } from "@/components/App";
import { NetworkError } from "@/api/client";
import { MAX_ATTEMPTS, STALE_TIME_MS } from "@/api/queryKeys";

import "@/styles/index.css";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: STALE_TIME_MS,
      refetchOnWindowFocus: false,
      // Only a request that never completed is worth retrying. A 409 or a 422 is
      // a definite answer, and repeating it three times would just repeat it.
      retry: (failureCount, error) =>
        error instanceof NetworkError && failureCount < MAX_ATTEMPTS - 1,
    },
    mutations: { retry: false },
  },
});

const mountPoint = document.getElementById("app");
if (mountPoint === null) {
  throw new Error("Venn Manager needs an #app element to mount into");
}

render(
  <QueryClientProvider client={queryClient}>
    <App />
  </QueryClientProvider>,
  mountPoint,
);
