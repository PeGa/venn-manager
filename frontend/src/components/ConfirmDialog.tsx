/**
 * Confirmation dialog.
 *
 * FRONTEND.md gates every destructive action behind one, and requires specific
 * warnings for concept deletion (its budgets and working-month records vanish)
 * and for concept renaming (the new name applies everywhere).
 */
import { Modal } from "./Modal";
import { useTranslation } from "@/hooks/useTranslation";

export interface ConfirmDialogProps {
  title: string;
  body: string;
  confirmLabel: string;
  /** Overrides the generic "Cancel", for dialogs whose refusal means something. */
  cancelLabel?: string;
  /** Renders the confirm button as a destructive action. */
  destructive?: boolean;
  busy?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmDialog({
  title,
  body,
  confirmLabel,
  cancelLabel,
  destructive = false,
  busy = false,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  const t = useTranslation();
  return (
    <Modal
      title={title}
      onClose={onCancel}
      footer={
        <>
          <button
            type="button"
            class="vm-button"
            onClick={onCancel}
            disabled={busy}
            data-testid="confirm-cancel"
          >
            {cancelLabel ?? t("cancel")}
          </button>
          <button
            type="button"
            class={destructive ? "vm-button-danger" : "vm-button-primary"}
            onClick={onConfirm}
            disabled={busy}
          >
            {busy ? t("loading") : confirmLabel}
          </button>
        </>
      }
    >
      <p>{body}</p>
    </Modal>
  );
}
