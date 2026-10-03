import { fireEvent, screen, waitFor, within } from "@solidjs/testing-library";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/ports/api";

import { createFakeApi } from "./fakeApi";
import { renderApp, text } from "./render";

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"], now: new Date("2026-09-28T10:00:00Z") });
});
afterEach(() => {
  vi.useRealTimers();
});

describe("Balance", () => {
  it("shows the household balance and this month's flows", async () => {
    renderApp(createFakeApi().api, "/balance");
    const hero = await screen.findByRole("region", { name: "Household balance" });
    expect(text(hero)).toContain("$14,985.48");
    expect(text(hero)).toContain("In $2,240.00 · Out $154.52 this month");
    expect(screen.queryByRole("region", { name: "What each member brings in" })).toBeNull();
  });

  it("lists member income when the household turned it on", async () => {
    const { api, state } = createFakeApi();
    state.household.showMemberIncome = true;
    renderApp(api, "/balance");
    const card = await screen.findByRole("region", { name: "What each member brings in" });
    expect(text(card)).toContain("Jordan");
    expect(text(card)).toContain("$2,240.00 this month");
    expect(text(card)).toContain("$4,480.00 all time");
  });
});

describe("Profile", () => {
  it("saves the real name on blur", async () => {
    const { api } = createFakeApi();
    renderApp(api, "/profile");
    const account = await screen.findByRole("region", { name: "Account" });
    const name = within(account).getByLabelText("Real name");
    fireEvent.input(name, { target: { value: "Alexandra" } });
    fireEvent.blur(name);
    await waitFor(() => expect(api.updateMe).toHaveBeenCalledWith({ realName: "Alexandra" }));
  });

  it("reports a taken username next to the field", async () => {
    const { api } = createFakeApi();
    api.updateMe.mockRejectedValueOnce(new ApiError(409, "DUPLICATE_NAME", "", "username"));
    renderApp(api, "/profile");
    const account = await screen.findByRole("region", { name: "Account" });
    const username = within(account).getByLabelText("Username");
    fireEvent.input(username, { target: { value: "jordan" } });
    fireEvent.keyDown(username, { key: "Enter" });
    expect(await within(account).findByText("That username is taken")).toBeTruthy();
  });

  it("switches language and theme", async () => {
    const { api } = createFakeApi();
    renderApp(api, "/profile");
    const prefs = await screen.findByRole("region", { name: "Preferences" });
    fireEvent.click(within(prefs).getByRole("button", { name: "Español" }));
    await waitFor(() => expect(api.updateMe).toHaveBeenCalledWith({ language: "es" }));
    expect(await screen.findByRole("heading", { name: "Perfil" })).toBeTruthy();
    fireEvent.click(within(await screen.findByRole("region", { name: "Preferencias" })).getByRole("button", { name: "Oscuro" }));
    await waitFor(() => expect(api.updateMe).toHaveBeenCalledWith({ theme: "dark" }));
    await waitFor(() => expect(document.documentElement.dataset["theme"]).toBe("dark"));
  });

  it("changes the password", async () => {
    const { api } = createFakeApi();
    renderApp(api, "/profile");
    const card = await screen.findByRole("region", { name: "Password" });
    fireEvent.input(within(card).getByLabelText("Current password"), { target: { value: "right-password" } });
    fireEvent.input(within(card).getByLabelText("New password"), { target: { value: "another-pass" } });
    fireEvent.input(within(card).getByLabelText("Repeat new password"), { target: { value: "another-pass" } });
    fireEvent.click(within(card).getByRole("button", { name: "Change password" }));
    expect(await within(card).findByText("Password changed")).toBeTruthy();
    expect(api.changePassword).toHaveBeenCalledWith("right-password", "another-pass");
  });

  it("signs out", async () => {
    const { api } = createFakeApi();
    renderApp(api, "/profile");
    fireEvent.click(await screen.findByRole("button", { name: "Sign out" }));
    expect(await screen.findByRole("heading", { name: "Sign in" })).toBeTruthy();
  });

  it("is reached from the sidebar", async () => {
    renderApp(createFakeApi().api, "/");
    fireEvent.click(await screen.findByRole("link", { name: /Signed in as Alex/ }));
    expect(await screen.findByRole("heading", { name: "Profile" })).toBeTruthy();
  });
});
