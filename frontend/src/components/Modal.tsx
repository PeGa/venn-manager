/**
 * Accessible modal dialog.
 *
 * AGENTS.md § Accessibility Baseline: focus is trapped, Escape dismisses, and
 * focus returns to whatever opened the dialog. The backdrop is deliberately not
 * clickable — an accidental click must not throw away a half-filled form.
 */
import type { ComponentChildren } from "preact";
import { useEffect, useId, useRef } from "preact/hooks";

const FOCUSABLE = [
  "a[href]",
  "button:not([disabled])",
  "input:not([disabled])",
  "select:not([disabled])",
  "textarea:not([disabled])",
  '[tabindex]:not([tabindex="-1"])',
].join(", ");

export interface ModalProps {
  title: string;
  onClose: () => void;
  children: ComponentChildren;
  footer?: ComponentChildren;
}

export function Modal({ title, onClose, children, footer }: ModalProps) {
  const panel = useRef<HTMLDivElement>(null);
  const titleId = useId();
  const opener = useRef<HTMLElement | null>(null);

  useEffect(() => {
    opener.current = document.activeElement as HTMLElement | null;
    const node = panel.current;
    const first = node?.querySelector<HTMLElement>(FOCUSABLE);
    (first ?? node)?.focus();

    const onKeyDown = (event: KeyboardEvent): void => {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
        return;
      }
      if (event.key !== "Tab" || node === null) {
        return;
      }
      const items = Array.from(node.querySelectorAll<HTMLElement>(FOCUSABLE));
      if (items.length === 0) {
        return;
      }
      const firstItem = items[0];
      const lastItem = items[items.length - 1];
      const active = document.activeElement;
      if (event.shiftKey && active === firstItem) {
        event.preventDefault();
        lastItem.focus();
      } else if (!event.shiftKey && active === lastItem) {
        event.preventDefault();
        firstItem.focus();
      }
    };

    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      opener.current?.focus();
    };
  }, [onClose]);

  return (
    <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div
        ref={panel}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        class="max-h-full w-full max-w-lg overflow-y-auto rounded-lg border border-border bg-canvas p-5 shadow-xl"
      >
        <h2 id={titleId} class="text-lg font-semibold text-ink">
          {title}
        </h2>
        <div class="mt-3 text-sm text-ink">{children}</div>
        {footer === undefined ? null : (
          <div class="mt-5 flex flex-wrap justify-end gap-2">{footer}</div>
        )}
      </div>
    </div>
  );
}
