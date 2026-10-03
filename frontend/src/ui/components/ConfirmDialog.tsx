/** A yes/no question before something destructive (FRONTEND.md § 4.5). */
import { Button } from "@/ui/components/basics";
import { Dialog } from "@/ui/components/Dialog";
import { useServices } from "@/ui/services";

export function ConfirmDialog(props: {
  title: string;
  body: string;
  confirmLabel: string;
  onConfirm: () => void;
  onClose: () => void;
}) {
  const { t } = useServices();
  return (
    <Dialog open title={props.title} onClose={() => props.onClose()}>
      <h2 class="text-[17px] font-bold">{props.title}</h2>
      <p class="mt-2 text-sm text-muted">{props.body}</p>
      <div class="mt-6 flex justify-end gap-2.5">
        <Button onClick={() => props.onClose()}>{t("action_cancel")}</Button>
        <Button kind="danger" onClick={() => props.onConfirm()}>
          {props.confirmLabel}
        </Button>
      </div>
    </Dialog>
  );
}
