/**
 * Form primitives.
 *
 * Every input has a real `<label>`, and an inline error is linked to its field
 * with `aria-describedby` and announced with `role="alert"` (AGENTS.md
 * § Accessibility Baseline and § Error Handling Patterns).
 */
import type { JSX } from "preact";
import { useId } from "preact/hooks";

import { useTranslation } from "@/hooks/useTranslation";
import type { TranslationKey } from "@/l10n";

export interface FieldProps {
  label: string;
  value: string;
  onInput: (value: string) => void;
  error?: TranslationKey | null;
  type?: string;
  required?: boolean;
  disabled?: boolean;
  autoComplete?: string;
  hint?: string;
  /** Lets a caller keep a stable id across renders; generated when omitted. */
  id?: string;
}

/** A labelled text-style input with an inline validation error. */
export function Field({
  label,
  value,
  onInput,
  error = null,
  type = "text",
  required = false,
  disabled = false,
  autoComplete,
  hint,
  id,
}: FieldProps) {
  const generated = useId();
  const fieldId = id ?? generated;
  const errorId = `${fieldId}-error`;
  const hintId = `${fieldId}-hint`;
  const t = useTranslation();
  const describedBy = [error === null ? null : errorId, hint === undefined ? null : hintId]
    .filter((part): part is string => part !== null)
    .join(" ");

  return (
    <div class="mb-3">
      <label class="vm-label" for={fieldId}>
        {label}
      </label>
      <input
        id={fieldId}
        class="vm-input"
        type={type}
        value={value}
        required={required}
        aria-required={required}
        disabled={disabled}
        autoComplete={autoComplete}
        aria-invalid={error !== null}
        aria-describedby={describedBy === "" ? undefined : describedBy}
        onInput={(event: JSX.TargetedEvent<HTMLInputElement>) =>
          onInput(event.currentTarget.value)
        }
      />
      {hint === undefined ? null : (
        <p id={hintId} class="mt-1 text-xs text-muted">
          {hint}
        </p>
      )}
      {error === null ? null : (
        <p id={errorId} class="vm-error" role="alert">
          {t(error)}
        </p>
      )}
    </div>
  );
}

export interface SelectFieldProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: Array<{ value: string; label: string }>;
  disabled?: boolean;
  error?: TranslationKey | null;
  hint?: string;
}

/** A labelled drop-down. Options carry their own labels, already translated. */
export function SelectField({
  label,
  value,
  onChange,
  options,
  disabled = false,
  error = null,
  hint,
}: SelectFieldProps) {
  const generated = useId();
  const errorId = `${generated}-error`;
  const t = useTranslation();

  return (
    <div class="mb-3">
      <label class="vm-label" for={generated}>
        {label}
      </label>
      <select
        id={generated}
        class="vm-input"
        value={value}
        disabled={disabled}
        aria-invalid={error !== null}
        aria-describedby={error === null ? undefined : errorId}
        onChange={(event: JSX.TargetedEvent<HTMLSelectElement>) =>
          onChange(event.currentTarget.value)
        }
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      {hint === undefined ? null : (
        <p class="mt-1 text-xs text-muted">{hint}</p>
      )}
      {error === null ? null : (
        <p id={errorId} class="vm-error" role="alert">
          {t(error)}
        </p>
      )}
    </div>
  );
}
