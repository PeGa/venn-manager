/**
 * Query error display.
 *
 * AGENTS.md § Error Handling Patterns: the user sees a localised message, never
 * a raw code, a server string or a stack trace. The server's own message is
 * logged for whoever is debugging, not rendered.
 */
import { ApiError } from "@/api/client";
import { errorKey } from "@/api/client";
import { useTranslation } from "@/hooks/useTranslation";

export interface ErrorNoticeProps {
  error: unknown;
  /** Lets the user retry a failed read. */
  onRetry?: () => void;
}

export function ErrorNotice({ error, onRetry }: ErrorNoticeProps) {
  const t = useTranslation();
  if (error instanceof ApiError) {
    console.warn("API error", error.code, error.status, error.message);
  } else {
    console.warn("Unexpected error", error);
  }

  return (
    <div
      class="vm-card border-negative"
      role="alert"
      aria-live="assertive"
      data-testid="error-notice"
    >
      <p class="font-medium text-negative">{t(errorKey(error))}</p>
      {onRetry === undefined ? null : (
        <button type="button" class="vm-button mt-3" onClick={onRetry}>
          {t("retry")}
        </button>
      )}
    </div>
  );
}

/** A loading placeholder that announces itself without stealing focus. */
export function LoadingNotice({ label }: { label: string }) {
  return (
    <p class="text-sm text-muted" aria-live="polite" data-testid="loading-notice">
      {label}
    </p>
  );
}
