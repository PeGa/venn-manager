/**
 * Form validation (AGENTS.md § TDD: form validation logic must be tested).
 *
 * These mirror the backend's rules so a submission is rejected in the browser
 * before it is rejected by the API. They are the single source of truth for the
 * inline errors shown next to a field, and the backend remains authoritative:
 * a 422 from the API is still surfaced.
 *
 * Every verdict is a translation key or null, never user-facing text, so a
 * component can render it through l10n and wire it to `aria-describedby`.
 */
import type { TranslationKey } from "@/l10n";

/** A validator's verdict: `null` when acceptable, else the message key. */
export type Verdict = TranslationKey | null;

/** DECIMAL(10,2): at most two decimals, within +/- 99,999,999.99. */
const AMOUNT_PATTERN = /^-?\d+(\.\d{1,2})?$/;
const MAX_AMOUNT = 99_999_999.99;

const DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/;

export const MIN_PASSWORD_LENGTH = 8;
export const MAX_CONCEPT_NAME_LENGTH = 64;
export const MAX_USERNAME_LENGTH = 64;
export const MAX_REAL_NAME_LENGTH = 128;

/** Reject empty or whitespace-only input. */
export function validateRequired(value: string): Verdict {
  return value.trim() === "" ? "validation_required" : null;
}

/**
 * Validate a monetary input.
 *
 * *required* is false for a budget amount, where empty means "no reserved
 * amount" rather than zero (FRONTEND.md § 2).
 */
export function validateAmount(value: string, required: boolean): Verdict {
  const trimmed = value.trim();
  if (trimmed === "") {
    return required ? "validation_required" : null;
  }
  if (!AMOUNT_PATTERN.test(trimmed)) {
    return "validation_amount";
  }
  if (Math.abs(Number(trimmed)) > MAX_AMOUNT) {
    return "validation_amount";
  }
  return null;
}

/** Validate a strict `YYYY-MM-DD` date that is also a real calendar date. */
export function validateDate(value: string): Verdict {
  const trimmed = value.trim();
  if (trimmed === "") {
    return "validation_required";
  }
  if (!DATE_PATTERN.test(trimmed)) {
    return "validation_date";
  }
  // Round-tripping catches impossible dates such as 2025-02-30, which the Date
  // constructor would silently roll into March.
  const parsed = new Date(`${trimmed}T00:00:00Z`);
  if (Number.isNaN(parsed.getTime())) {
    return "validation_date";
  }
  return parsed.toISOString().slice(0, 10) === trimmed ? null : "validation_date";
}

/** Validate a concept name: required, at most 64 characters. */
export function validateConceptName(value: string): Verdict {
  return validateLength(value, MAX_CONCEPT_NAME_LENGTH, "validation_concept_name");
}

/** Validate a username: required, at most 64 characters. */
export function validateUsername(value: string): Verdict {
  return validateLength(value, MAX_USERNAME_LENGTH, "validation_username");
}

/** Validate a real name: required, at most 128 characters. */
export function validateRealName(value: string): Verdict {
  return validateLength(value, MAX_REAL_NAME_LENGTH, "validation_real_name");
}

/** Validate a password against the documented minimum length. */
export function validatePassword(value: string): Verdict {
  if (value === "") {
    return "validation_required";
  }
  return value.length < MIN_PASSWORD_LENGTH ? "validation_password_short" : null;
}

/** Validate that a repeated password matches. Whitespace is significant. */
export function validatePasswordMatch(value: string, repeat: string): Verdict {
  return value === repeat ? null : "validation_password_mismatch";
}

/**
 * Validate the currency symbol as exactly one grapheme cluster.
 *
 * `Intl.Segmenter` rather than `length`: a ZWJ emoji is one symbol to the user
 * and several code points to JavaScript, and FRONTEND.md § 5.1.3 explicitly
 * allows it while rejecting "USD".
 */
export function validateCurrency(value: string): Verdict {
  const trimmed = value.trim();
  if (trimmed === "") {
    return "validation_required";
  }
  return countGraphemes(trimmed) === 1 ? null : "validation_currency";
}

function validateLength(
  value: string,
  maxLength: number,
  tooLongKey: TranslationKey,
): Verdict {
  const trimmed = value.trim();
  if (trimmed === "") {
    return "validation_required";
  }
  return trimmed.length > maxLength ? tooLongKey : null;
}

function countGraphemes(value: string): number {
  const segmenter = new Intl.Segmenter(undefined, { granularity: "grapheme" });
  return [...segmenter.segment(value)].length;
}
