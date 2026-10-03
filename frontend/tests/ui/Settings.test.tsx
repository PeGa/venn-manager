import { fireEvent, screen, waitFor, within } from "@solidjs/testing-library";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { createFakeApi } from "./fakeApi";
import { renderApp, text } from "./render";

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"], now: new Date("2026-09-28T10:00:00Z") });
});
afterEach(() => {
  vi.useRealTimers();
});

const region = (name: string) => screen.findByRole("region", { name });

describe("Settings · currency sign", () => {
  it("saves a quick chip at once and typed text after a pause", async () => {
    const { api } = createFakeApi();
    renderApp(api, "/settings");
    const card = await region("Currency sign");
    fireEvent.click(within(card).getByRole("button", { name: "€" }));
    await waitFor(() => expect(api.updateHousehold).toHaveBeenCalledWith({ currencySign: "€" }));
    fireEvent.input(within(card).getByLabelText("Currency sign"), { target: { value: "CHF" } });
    await waitFor(() => expect(api.updateHousehold).toHaveBeenCalledWith({ currencySign: "CHF" }));
  });

  it("rejects signs longer than 8 characters", async () => {
    renderApp(createFakeApi().api, "/settings");
    const card = await region("Currency sign");
    const input = within(card).getByLabelText<HTMLInputElement>("Currency sign");
    expect(input.maxLength).toBe(8);
  });
});

describe("Settings · household", () => {
  it("saves the name on blur, the time zone and the toggle on change", async () => {
    const { api } = createFakeApi();
    renderApp(api, "/settings");
    const card = await region("Household");
    const name = within(card).getByLabelText("Name");
    fireEvent.input(name, { target: { value: "Casa" } });
    fireEvent.blur(name);
    await waitFor(() => expect(api.updateHousehold).toHaveBeenCalledWith({ name: "Casa" }));
    fireEvent.change(within(card).getByLabelText("Time zone"), { target: { value: "Europe/Madrid" } });
    await waitFor(() => expect(api.updateHousehold).toHaveBeenCalledWith({ timezone: "Europe/Madrid" }));
    fireEvent.click(within(card).getByRole("checkbox", { name: "Show what each member brings in" }));
    await waitFor(() => expect(api.updateHousehold).toHaveBeenCalledWith({ showMemberIncome: true }));
  });

  it("saves a valid opening balance in cents and flags an invalid one", async () => {
    const { api } = createFakeApi();
    renderApp(api, "/settings");
    const card = await region("Household");
    const balance = within(card).getByLabelText("Opening balance");
    fireEvent.input(balance, { target: { value: "-1250.5" } });
    fireEvent.blur(balance);
    await waitFor(() => expect(api.updateHousehold).toHaveBeenCalledWith({ openingBalance: -125050 }));
    fireEvent.input(balance, { target: { value: "a lot" } });
    fireEvent.blur(balance);
    expect(await within(card).findByText("Enter an amount like 1250.50")).toBeTruthy();
  });
});

describe("Settings · members", () => {
  it("lists members with role and spend", async () => {
    renderApp(createFakeApi().api, "/settings");
    const card = await region("Members");
    expect(text(card)).toContain("Alex");
    expect(text(card)).toContain("Admin · $84 spent");
    expect(text(card)).toContain("Member · $0 spent");
  });

  it("removes a member after confirmation, never yourself", async () => {
    const { api } = createFakeApi();
    renderApp(api, "/settings");
    const card = await region("Members");
    expect(within(card).getAllByRole("button", { name: /^Remove/ })).toHaveLength(1);
    fireEvent.click(within(card).getByRole("button", { name: "Remove Jordan" }));
    const dialog = await screen.findByRole("dialog", { name: "Remove Jordan?" });
    fireEvent.click(within(dialog).getByRole("button", { name: "Remove" }));
    await waitFor(() => expect(api.removeMember).toHaveBeenCalledWith("m-jordan"));
  });

  it("invites with a dialog and shows a taken username inline", async () => {
    const { api } = createFakeApi();
    renderApp(api, "/settings");
    const card = await region("Members");
    fireEvent.input(within(card).getByLabelText("Name to invite"), { target: { value: "Dev" } });
    fireEvent.click(within(card).getByRole("button", { name: "Invite" }));
    const dialog = await screen.findByRole("dialog", { name: "Add a member" });
    expect(within(dialog).getByLabelText<HTMLInputElement>("Real name").value).toBe("Dev");
    fireEvent.input(within(dialog).getByLabelText("Username"), { target: { value: "jordan" } });
    fireEvent.input(within(dialog).getByLabelText("Initial password"), { target: { value: "first-pass" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Invite" }));
    expect(await within(dialog).findByText("That username is taken")).toBeTruthy();
    fireEvent.input(within(dialog).getByLabelText("Username"), { target: { value: "dev" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Invite" }));
    await waitFor(() =>
      expect(api.createMember).toHaveBeenLastCalledWith({
        username: "dev",
        realName: "Dev",
        password: "first-pass",
        isAdmin: false,
      }),
    );
  });

  it("edits an account from its row", async () => {
    const { api } = createFakeApi();
    renderApp(api, "/settings");
    const card = await region("Members");
    fireEvent.click(within(card).getByRole("button", { name: /Edit Jordan/ }));
    const dialog = await screen.findByRole("dialog", { name: "Jordan's account" });
    fireEvent.click(within(dialog).getByRole("checkbox", { name: "Admin" }));
    fireEvent.click(within(dialog).getByRole("button", { name: "Save" }));
    await waitFor(() => expect(api.updateMember).toHaveBeenCalledWith("m-jordan", { isAdmin: true }));
  });

  it("shows members without controls to non-admins", async () => {
    const { api, state } = createFakeApi();
    state.session!.member.role = "member";
    renderApp(api, "/settings");
    const card = await region("Members");
    expect(within(card).queryByRole("button")).toBeNull();
    expect(within(card).queryByLabelText("Name to invite")).toBeNull();
  });
});

describe("Settings · budget concepts", () => {
  it("adds concepts and reports duplicates inline", async () => {
    const { api } = createFakeApi();
    renderApp(api, "/settings");
    const card = await region("Budget concepts");
    const input = within(card).getByLabelText("New concept");
    fireEvent.input(input, { target: { value: "groceries" } });
    fireEvent.click(within(card).getByRole("button", { name: "Add" }));
    expect(await within(card).findByText("That name is already used")).toBeTruthy();
    fireEvent.input(input, { target: { value: " Pets " } });
    fireEvent.click(within(card).getByRole("button", { name: "Add" }));
    await waitFor(() => expect(api.createBudget).toHaveBeenLastCalledWith("Pets"));
  });

  it("renames inline", async () => {
    const { api } = createFakeApi();
    renderApp(api, "/settings");
    const card = await region("Budget concepts");
    fireEvent.click(within(card).getByRole("button", { name: "Rename Dining out" }));
    const input = within(card).getByLabelText("Name of Dining out");
    fireEvent.input(input, { target: { value: "Eating out" } });
    fireEvent.keyDown(input, { key: "Enter" });
    await waitFor(() => expect(api.updateBudget).toHaveBeenCalledWith("b-dining", { name: "Eating out" }));
  });

  it("removes a concept after a warning", async () => {
    const { api } = createFakeApi();
    renderApp(api, "/settings");
    const card = await region("Budget concepts");
    fireEvent.click(within(card).getByRole("button", { name: "Remove Lisbon trip" }));
    const dialog = await screen.findByRole("dialog", { name: "Remove Lisbon trip?" });
    expect(text(dialog)).toContain("stop counting in every total, past months included");
    fireEvent.click(within(dialog).getByRole("button", { name: "Remove" }));
    await waitFor(() => expect(api.deleteBudget).toHaveBeenCalledWith("b-trip"));
  });
});
