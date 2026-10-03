/**
 * Small shared building blocks. Visual values come from the design tokens
 * in src/styles/index.css.
 */
import { Show, splitProps, type JSX, type ParentProps } from "solid-js";

export function Card(props: ParentProps<{ class?: string; tight?: boolean }>) {
  return (
    <section
      class={`rounded-card border border-card-border bg-card ${props.tight === true ? "px-4 py-3" : "px-[22px] py-5"} ${props.class ?? ""}`}
    >
      {props.children}
    </section>
  );
}

export function CardTitle(props: ParentProps<{ subtitle?: string; aside?: JSX.Element }>) {
  return (
    <header class="flex items-baseline justify-between gap-3">
      <div>
        <h2 class="text-[15px] font-bold">{props.children}</h2>
        <Show when={props.subtitle}>
          <p class="mt-0.5 text-xs text-muted">{props.subtitle}</p>
        </Show>
      </div>
      {props.aside}
    </header>
  );
}

export function Avatar(props: { initial: string; color: string; size?: number; dimmed?: boolean }) {
  const size = () => props.size ?? 34;
  return (
    <span
      aria-hidden="true"
      class="grid flex-none place-items-center rounded-full text-xs font-semibold text-[#1e1d1a]"
      classList={{ "opacity-50": props.dimmed === true }}
      style={{ width: `${String(size())}px`, height: `${String(size())}px`, background: props.color }}
    >
      {props.initial}
    </span>
  );
}

export function Bar(props: { pct: number; alert?: boolean; onDark?: boolean; label: string }) {
  return (
    <div
      role="progressbar"
      aria-label={props.label}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={Math.round(props.pct)}
      class="h-2 overflow-hidden rounded"
      classList={{ "bg-white/15": props.onDark === true, "bg-hairline": props.onDark !== true }}
    >
      <div
        class="h-full rounded"
        classList={{
          "bg-bar-light": props.onDark === true,
          "bg-coral": props.onDark !== true && props.alert === true,
          "bg-bar": props.onDark !== true && props.alert !== true,
        }}
        style={{ width: `${String(Math.min(100, Math.max(0, props.pct)))}%` }}
      />
    </div>
  );
}

type ButtonKind = "primary" | "secondary" | "danger" | "quiet";

const BUTTON: Record<ButtonKind, string> = {
  primary: "border-primary bg-primary text-white dark:border-accent dark:bg-accent dark:text-canvas",
  secondary: "border-input-border bg-card text-ink",
  danger: "border-[#e0c3b9] bg-card text-coral-text dark:border-coral-tint",
  quiet: "border-transparent bg-transparent text-accent",
};

export function Button(
  props: ParentProps<
    JSX.ButtonHTMLAttributes<HTMLButtonElement> & { kind?: ButtonKind; small?: boolean }
  >,
) {
  const [local, rest] = splitProps(props, ["kind", "small", "class", "children"]);
  return (
    <button
      type="button"
      {...rest}
      class={`rounded-control border font-semibold disabled:cursor-not-allowed disabled:border-disabled-bg disabled:bg-disabled-bg disabled:text-disabled-text ${local.small === true ? "px-3 py-1.5 text-xs" : "px-[18px] py-2.5 text-sm"} ${BUTTON[local.kind ?? "secondary"]} ${local.class ?? ""}`}
    >
      {local.children}
    </button>
  );
}

export function Chip(props: ParentProps<{ active: boolean; onClick: () => void; mono?: boolean }>) {
  return (
    <button
      type="button"
      aria-pressed={props.active}
      onClick={() => props.onClick()}
      class="flex-none rounded-chip border border-input-border px-3 py-1.5 text-xs font-semibold"
      classList={{
        "bg-primary text-white": props.active,
        "bg-card text-ink": !props.active,
        "font-mono text-[15px]": props.mono === true,
      }}
    >
      {props.children}
    </button>
  );
}

export function Field(
  props: JSX.InputHTMLAttributes<HTMLInputElement> & {
    label: string;
    error?: string | undefined;
    hideLabel?: boolean;
    mono?: boolean;
  },
) {
  const [local, rest] = splitProps(props, ["label", "error", "hideLabel", "mono", "class", "id"]);
  const id = () => local.id ?? `field-${local.label.replace(/\W+/g, "-").toLowerCase()}`;
  return (
    <div class={`flex min-w-0 flex-col gap-1 ${local.class ?? ""}`}>
      <label for={id()} class="text-xs font-semibold text-muted" classList={{ "sr-only": local.hideLabel === true }}>
        {local.label}
      </label>
      <input
        id={id()}
        {...rest}
        aria-invalid={local.error !== undefined}
        aria-describedby={local.error !== undefined ? `${id()}-error` : undefined}
        class="w-full min-w-0 rounded-control border border-input-border bg-input-bg px-3 py-2.5 text-sm text-ink placeholder:text-faint"
        classList={{ "font-mono": local.mono === true, "border-coral": local.error !== undefined }}
      />
      <Show when={local.error}>
        <p id={`${id()}-error`} class="text-xs text-coral-text">
          {local.error}
        </p>
      </Show>
    </div>
  );
}

export function Notice(props: ParentProps<{ onDismiss?: () => void; action?: JSX.Element }>) {
  return (
    <div role="status" class="flex items-center gap-3 rounded-control border border-coral-tint bg-coral-tint px-4 py-3 text-sm text-coral-text">
      <span class="flex-1">{props.children}</span>
      {props.action}
      <Show when={props.onDismiss}>
        {(dismiss) => (
          <button type="button" aria-label="×" class="text-lg leading-none" onClick={() => dismiss()()}>
            ×
          </button>
        )}
      </Show>
    </div>
  );
}

export function Skeleton(props: { lines?: number }) {
  return (
    <div aria-hidden="true" class="flex animate-pulse flex-col gap-3 rounded-card border border-card-border bg-card p-5">
      {Array.from({ length: props.lines ?? 3 }, () => (
        <div class="h-4 rounded bg-hairline" />
      ))}
    </div>
  );
}
