/**
 * Native `<dialog>`: a centered modal with a fine pointer, a bottom sheet with
 * a coarse one (FRONTEND.md § 4.4). Escape, the scrim and Cancel close it;
 * the browser traps focus and restores it to the trigger.
 */
import { createEffect, onCleanup, type ParentProps } from "solid-js";

import { useServices } from "@/ui/services";

export function Dialog(props: ParentProps<{ open: boolean; title: string; onClose: () => void }>) {
  const { coarse } = useServices();
  let dialog: HTMLDialogElement | undefined;

  createEffect(() => {
    if (dialog === undefined) return;
    if (props.open && !dialog.open) {
      dialog.showModal();
    } else if (!props.open && dialog.open) {
      dialog.close();
    }
  });
  onCleanup(() => dialog?.close());

  return (
    <dialog
      ref={dialog}
      aria-label={props.title}
      onCancel={(event) => {
        event.preventDefault();
        props.onClose();
      }}
      onClick={(event) => {
        if (event.target === dialog) props.onClose();
      }}
      class="bg-card text-ink shadow-modal backdrop:bg-scrim"
      classList={{
        "m-auto w-[min(480px,calc(100vw-32px))] rounded-card p-6": !coarse(),
        "mx-0 mb-0 mt-auto w-full max-w-none rounded-t-card p-5 pb-8": coarse(),
      }}
    >
      {props.children}
    </dialog>
  );
}
