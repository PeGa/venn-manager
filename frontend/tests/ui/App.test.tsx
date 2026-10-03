import { fireEvent, screen, waitFor } from "@solidjs/testing-library";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { createFakeApi } from "./fakeApi";
import { renderApp, text } from "./render";

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"], now: new Date("2026-09-28T10:00:00Z") });
});
afterEach(() => {
  vi.useRealTimers();
});

describe("session gate", () => {
  it("asks to sign in without a session and rejects wrong passwords", async () => {
    const { api, state } = createFakeApi();
    state.session = null;
    renderApp(api);
    fireEvent.input(await screen.findByLabelText("Username"), { target: { value: "alex" } });
    fireEvent.input(screen.getByLabelText("Password"), { target: { value: "nope" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(text(await screen.findByRole("alert"))).toContain("Invalid username or password");
  });

  it("enters the app after signing in", async () => {
    const { api, state } = createFakeApi();
    state.session = null;
    renderApp(api);
    fireEvent.input(await screen.findByLabelText("Username"), { target: { value: "alex" } });
    fireEvent.input(screen.getByLabelText("Password"), { target: { value: "right-password" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByRole("heading", { name: "Overview" })).toBeTruthy();
  });

  it("forces a password change, then lets the member in", async () => {
    const { api, state } = createFakeApi();
    state.session!.mustChangePassword = true;
    renderApp(api);
    expect(await screen.findByRole("heading", { name: "Choose a password" })).toBeTruthy();
    fireEvent.input(screen.getByLabelText("Current password"), { target: { value: "right-password" } });
    fireEvent.input(screen.getByLabelText("New password"), { target: { value: "short" } });
    fireEvent.input(screen.getByLabelText("Repeat new password"), { target: { value: "short" } });
    fireEvent.click(screen.getByRole("button", { name: "Change password" }));
    expect(await screen.findByText("Use 8 to 128 characters")).toBeTruthy();
    fireEvent.input(screen.getByLabelText("New password"), { target: { value: "long-enough" } });
    fireEvent.input(screen.getByLabelText("Repeat new password"), { target: { value: "long-enough" } });
    fireEvent.click(screen.getByRole("button", { name: "Change password" }));
    expect(await screen.findByRole("heading", { name: "Overview" })).toBeTruthy();
  });

  it("reports a wrong current password next to its field", async () => {
    const { api, state } = createFakeApi();
    state.session!.mustChangePassword = true;
    renderApp(api);
    fireEvent.input(await screen.findByLabelText("Current password"), { target: { value: "wrong-one" } });
    fireEvent.input(screen.getByLabelText("New password"), { target: { value: "long-enough" } });
    fireEvent.input(screen.getByLabelText("Repeat new password"), { target: { value: "long-enough" } });
    fireEvent.click(screen.getByRole("button", { name: "Change password" }));
    expect(await screen.findByText("The current password is wrong")).toBeTruthy();
  });

  it("lets a restricted session log out", async () => {
    const { api, state } = createFakeApi();
    state.session!.mustChangePassword = true;
    renderApp(api);
    fireEvent.click(await screen.findByRole("button", { name: "Log out" }));
    await waitFor(() => expect(api.logout).toHaveBeenCalled());
    expect(await screen.findByRole("heading", { name: "Sign in" })).toBeTruthy();
  });

  it("follows the member's language", async () => {
    const { api, state } = createFakeApi();
    state.session!.preferences.language = "es";
    renderApp(api);
    expect(await screen.findByRole("heading", { name: "Resumen" })).toBeTruthy();
  });
});
