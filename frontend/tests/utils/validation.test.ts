import { describe, expect, it } from "vitest";

import {
  validateAmount,
  validateConceptName,
  validateCurrency,
  validateDate,
  validatePassword,
  validatePasswordMatch,
  validateRealName,
  validateRequired,
  validateUsername,
} from "@/utils/validation";

describe("validateRequired", () => {
  it("rejects empty and whitespace-only input", () => {
    expect(validateRequired("")).toBe("validation_required");
    expect(validateRequired("   ")).toBe("validation_required");
  });

  it("accepts any visible character", () => {
    expect(validateRequired("x")).toBeNull();
  });
});

describe("validateAmount", () => {
  it("accepts up to two decimals", () => {
    expect(validateAmount("45.50", true)).toBeNull();
    expect(validateAmount("45", true)).toBeNull();
    expect(validateAmount("0.1", true)).toBeNull();
  });

  it("accepts a negative amount", () => {
    // The backend allows negatives; the flow comes from the concept.
    expect(validateAmount("-12.50", true)).toBeNull();
  });

  it("rejects excessive precision", () => {
    expect(validateAmount("45.567", true)).toBe("validation_amount");
    expect(validateAmount("0.001", true)).toBe("validation_amount");
  });

  it("rejects non-numeric input", () => {
    expect(validateAmount("lots", true)).toBe("validation_amount");
    expect(validateAmount("1e5", true)).toBe("validation_amount");
    expect(validateAmount("1,5", true)).toBe("validation_amount");
    expect(validateAmount("12.34.56", true)).toBe("validation_amount");
  });

  it("requires a value for a transaction", () => {
    expect(validateAmount("", true)).toBe("validation_required");
    expect(validateAmount("   ", true)).toBe("validation_required");
  });

  it("allows an empty amount for a budget", () => {
    // FRONTEND.md § 2: an empty amount means no reserved amount, not zero.
    expect(validateAmount("", false)).toBeNull();
  });

  it("rejects an out-of-range amount", () => {
    expect(validateAmount("100000000.00", true)).toBe("validation_amount");
  });
});

describe("validateDate", () => {
  it("accepts a real ISO date", () => {
    expect(validateDate("2025-07-15")).toBeNull();
    expect(validateDate("2024-02-29")).toBeNull();
  });

  it("rejects an impossible date", () => {
    expect(validateDate("2025-02-30")).toBe("validation_date");
    expect(validateDate("2023-02-29")).toBe("validation_date");
    expect(validateDate("2025-13-01")).toBe("validation_date");
  });

  it("rejects a wrong format", () => {
    expect(validateDate("15/07/2025")).toBe("validation_date");
    expect(validateDate("2025-7-5")).toBe("validation_date");
  });

  it("rejects an empty date", () => {
    expect(validateDate("")).toBe("validation_required");
  });
});

describe("validateConceptName", () => {
  it("accepts a name within the limit", () => {
    expect(validateConceptName("Groceries")).toBeNull();
    expect(validateConceptName("x".repeat(64))).toBeNull();
  });

  it("rejects an overlong name", () => {
    expect(validateConceptName("x".repeat(65))).toBe("validation_concept_name");
  });

  it("rejects an empty name", () => {
    expect(validateConceptName("  ")).toBe("validation_required");
  });
});

describe("validateCurrency", () => {
  it("accepts a single-character symbol", () => {
    expect(validateCurrency("$")).toBeNull();
    expect(validateCurrency("€")).toBeNull();
  });

  it("accepts a multi-codepoint emoji as one grapheme", () => {
    // FRONTEND.md § 5.1.3: a clown emoji is allowed, "USD" is not.
    const family = "\u{1F468}\u200D\u{1F469}\u200D\u{1F467}";
    expect(family.length).toBeGreaterThan(1);
    expect(validateCurrency(family)).toBeNull();
  });

  it("rejects more than one grapheme", () => {
    expect(validateCurrency("USD")).toBe("validation_currency");
    expect(validateCurrency("$$")).toBe("validation_currency");
  });

  it("rejects an empty value", () => {
    expect(validateCurrency("")).toBe("validation_required");
  });
});

describe("validatePassword", () => {
  it("accepts eight characters or more", () => {
    expect(validatePassword("12345678")).toBeNull();
  });

  it("rejects a short password", () => {
    expect(validatePassword("short")).toBe("validation_password_short");
  });

  it("rejects an empty password", () => {
    expect(validatePassword("")).toBe("validation_required");
  });
});

describe("validatePasswordMatch", () => {
  it("accepts identical values", () => {
    expect(validatePasswordMatch("a-password", "a-password")).toBeNull();
  });

  it("rejects a mismatch", () => {
    expect(validatePasswordMatch("a-password", "another")).toBe(
      "validation_password_mismatch",
    );
  });

  it("treats surrounding whitespace as significant", () => {
    expect(validatePasswordMatch("a-password", "a-password ")).toBe(
      "validation_password_mismatch",
    );
  });
});

describe("validateUsername", () => {
  it("accepts a username within the limit", () => {
    expect(validateUsername("alice")).toBeNull();
    expect(validateUsername("x".repeat(64))).toBeNull();
  });

  it("rejects an overlong username", () => {
    expect(validateUsername("x".repeat(65))).toBe("validation_username");
  });

  it("rejects an empty username", () => {
    expect(validateUsername("  ")).toBe("validation_required");
  });
});

describe("validateRealName", () => {
  it("accepts a name within the limit", () => {
    expect(validateRealName("Alice Doe")).toBeNull();
    expect(validateRealName("x".repeat(128))).toBeNull();
  });

  it("rejects an overlong name", () => {
    expect(validateRealName("x".repeat(129))).toBe("validation_real_name");
  });
});
