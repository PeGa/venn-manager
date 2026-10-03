import { describe, expect, it } from "vitest";

import { passwordProblem } from "@/domain/passwords";

describe("passwordProblem", () => {
  it("accepts 8 to 128 matching characters", () => {
    expect(passwordProblem("12345678", "12345678")).toBeNull();
    expect(passwordProblem("x".repeat(128), "x".repeat(128))).toBeNull();
  });

  it("reports the length first, then a mismatch", () => {
    expect(passwordProblem("short", "other")).toBe("length");
    expect(passwordProblem("x".repeat(129), "x".repeat(129))).toBe("length");
    expect(passwordProblem("12345678", "12345679")).toBe("mismatch");
  });
});
