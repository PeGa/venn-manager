import { describe, expect, it } from "vitest";

import { activitySection, sentence } from "@/domain/activity";
import type { ActivityEntry } from "@/domain/model";

function entry(action: ActivityEntry["action"], params: ActivityEntry["params"], target: ActivityEntry["target"] = { type: "none" }): ActivityEntry {
  return { id: "1", actorId: "m", action, params, at: "2026-09-28T10:00:00Z", target };
}

describe("sentence", () => {
  it.each([
    [entry("tx.create", { category: "Groceries", amount: -8412 }), "added −$84.12 to Groceries"],
    [entry("tx.update", { category: "Paycheck", amount: 224000 }), "edited +$2,240.00 in Paycheck"],
    [entry("tx.delete", { category: "Dining out", amount: -640 }), "removed −$6.40 from Dining out"],
    [entry("tx.bulkDelete", { count: 3 }), "removed 3 transactions"],
    [entry("tx.bulkDelete", { count: 1 }), "removed 1 transaction"],
    [entry("budget.create", { name: "Fun" }), "added the Fun budget"],
    [entry("budget.rename", { oldName: "Grocery", name: "Groceries" }), "renamed Grocery to Groceries"],
    [entry("budget.amount", { name: "Dining out", amount: -35000 }), "set the Dining out budget to −$350"],
    [entry("budget.schedule", { name: "Rent" }), "changed when Rent is due"],
    [entry("budget.goal", { name: "Trip", goal: true }), "made Trip a goal"],
    [entry("budget.goal", { name: "Trip", goal: false }), "moved Trip back to Budget"],
    [entry("budget.delete", { name: "Fun" }), "removed the Fun budget"],
    [entry("member.invite", { name: "Dev" }), "added Dev to the household"],
    [entry("member.update", { name: "Dev" }), "updated Dev's account"],
    [entry("member.remove", { name: "Dev" }), "removed Dev from the household"],
    [entry("settings.currency", { sign: "€" }), "changed the currency sign to €"],
    [entry("settings.currency", { sign: "" }), "removed the currency sign"],
    [entry("settings.name", { name: "Casa" }), "renamed the household to Casa"],
    [entry("settings.timezone", { timezone: "Europe/Madrid" }), "changed the timezone to Europe/Madrid"],
    [entry("settings.openingBalance", { amount: 125050 }), "set the opening balance to $1,250.50"],
    [entry("settings.memberIncome", { enabled: true }), "turned member income on"],
    [entry("settings.memberIncome", { enabled: false }), "turned member income off"],
  ])("%#: %s", (activity, expected) => {
    expect(sentence("en", activity, "$")).toBe(expected);
  });

  it("speaks Spanish", () => {
    expect(sentence("es", entry("tx.create", { category: "Mercado", amount: -500 }), "$")).toBe(
      "añadió −$5.00 a Mercado",
    );
  });
});

describe("activitySection", () => {
  it("follows the target, then the action", () => {
    expect(activitySection(entry("tx.update", {}, { type: "transaction", id: "t", archived: true, month: "2026-08" }))).toBe("history");
    expect(activitySection(entry("tx.update", {}, { type: "transaction", id: "t", archived: false, month: "2026-09" }))).toBe("transactions");
    expect(activitySection(entry("budget.amount", {}, { type: "budget", id: "b", goal: true }))).toBe("goals");
    expect(activitySection(entry("budget.delete", {}))).toBe("budget");
    expect(activitySection(entry("tx.bulkDelete", {}))).toBe("transactions");
    expect(activitySection(entry("member.remove", {}))).toBe("settings");
    expect(activitySection(entry("settings.name", {}, { type: "settings", section: "household" }))).toBe("settings");
  });
});
