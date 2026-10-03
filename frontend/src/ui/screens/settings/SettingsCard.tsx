/** A Settings card that activity navigation can highlight (FRONTEND.md § 7.2). */
import type { ParentProps } from "solid-js";

import { Highlight } from "@/ui/components/Highlight";

export function SettingsCard(props: ParentProps<{ section: string; title: string; subtitle?: string }>) {
  return (
    <Highlight key={`settings:${props.section}`} class="rounded-[20px]">
      <section aria-label={props.title} class="rounded-[20px] border-[1.5px] border-card-border bg-card p-5">
        <h2 class="font-bold">{props.title}</h2>
        <p class="mb-3 mt-0.5 text-xs text-muted">{props.subtitle}</p>
        {props.children}
      </section>
    </Highlight>
  );
}
