/** Render the whole app at a route, around a fake API. */
import { render } from "@solidjs/testing-library";

import type { Api } from "@/ports/api";
import { App } from "@/ui/App";

export function renderApp(api: Api, path = "/") {
  window.history.replaceState(null, "", path);
  return render(() => <App makeApi={() => api} />);
}

/** An element's visible text with whitespace collapsed. */
export function text(element: Element | null): string {
  return (element?.textContent ?? "").replace(/\s+/g, " ").trim();
}
