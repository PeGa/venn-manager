/**
 * The session gate in App (FRONTEND.md § General description, API_SURFACE.md
 * § Force Password Change).
 *
 * `GET /auth/session` is the only way the client learns who is signed in, and it
 * answers a restricted session with a 403 rather than a payload. These tests pin
 * that all three outcomes land on the right screen — getting it wrong either
 * shows a signed-in user the login form or hides the forced-change screen behind
 * it.
 */
import { fireEvent, screen, waitFor } from "@testing-library/preact";
import { afterEach, describe, expect, it, vi } from "vitest";

import { App } from "@/components/App";
import { renderWithProviders, stubApi } from "../helpers";

const SESSION = {
  user: { id: 1, username: "admin", real_name: "Administrator", is_admin: true },
  must_change_password: false,
};

const RESTRICTED = {
  code: "PASSWORD_CHANGE_REQUIRED",
  message: "Password change required before continuing",
};

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("App session gate", () => {
  it("shows the login screen when there is no session", async () => {
    stubApi([
      {
        match: /\/auth\/session/,
        status: 401,
        error: { code: "UNAUTHORIZED", message: "No active session" },
      },
    ]);

    renderWithProviders(<App />);

    await waitFor(() => expect(screen.getByTestId("sign-in")).toBeTruthy());
    expect(screen.queryByTestId("force-change-submit")).toBeNull();
  });

  it("shows the password form for a restricted session", async () => {
    // A refresh while the gate is up must not look like a signed-out user.
    stubApi([{ match: /\/auth\/session/, status: 403, error: RESTRICTED }]);

    renderWithProviders(<App />);

    await waitFor(() => expect(screen.getByTestId("force-change-submit")).toBeTruthy());
    expect(screen.queryByTestId("sign-in")).toBeNull();
  });

  it("lets a restricted session log out", async () => {
    const fetchMock = stubApi([
      { match: /\/auth\/logout/, method: "POST" },
      { match: /\/auth\/session/, status: 403, error: RESTRICTED },
    ]);

    renderWithProviders(<App />);
    await waitFor(() => expect(screen.getByTestId("force-change-logout")).toBeTruthy());

    fireEvent.click(screen.getByTestId("force-change-logout"));

    await waitFor(() =>
      expect(
        fetchMock.mock.calls.some(
          ([url, init]) =>
            String(url).endsWith("/auth/logout") &&
            (init as RequestInit | undefined)?.method === "POST",
        ),
      ).toBe(true),
    );
  });

  it("shows the password form when login reports must_change_password", async () => {
    stubApi([
      { match: /\/auth\/session/, data: { ...SESSION, must_change_password: true } },
    ]);

    renderWithProviders(<App />);

    await waitFor(() => expect(screen.getByTestId("force-change-submit")).toBeTruthy());
  });
});
