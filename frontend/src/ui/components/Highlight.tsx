/**
 * Wraps a record that activity navigation can point at (FRONTEND.md § 7.2).
 * While highlighted it scrolls into view and shows the highlight colors.
 */
import { createEffect, type ParentProps } from "solid-js";

import { useServices } from "@/ui/services";

export function useHighlight(key: () => string) {
  const { highlighted } = useServices();
  return () => highlighted() === key();
}

export function Highlight(props: ParentProps<{ key: string; class?: string; rounded?: string }>) {
  const active = useHighlight(() => props.key);
  let element: HTMLDivElement | undefined;
  createEffect(() => {
    if (active()) element?.scrollIntoView({ block: "center", behavior: "smooth" });
  });
  return (
    <div
      ref={element}
      data-highlight={props.key}
      class={`transition-colors ${props.class ?? ""}`}
      classList={{ "bg-highlight outline outline-[1.5px] outline-accent": active() }}
    >
      {props.children}
    </div>
  );
}
