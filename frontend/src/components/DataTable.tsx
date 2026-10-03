/**
 * The grid every screen is built from.
 *
 * A real `<table>` with a caption and column headers (AGENTS.md § Accessibility
 * Baseline). Rows are always in id order — the contract fixes creation order and
 * offers no sort control, so none is rendered.
 *
 * Selection uses a checkbox per row rather than a bare click handler, so the
 * multi-select delete is reachable from the keyboard as well as by touch.
 */
import type { ComponentChild } from "preact";

import { useTranslation } from "@/hooks/useTranslation";

export interface Column<T> {
  key: string;
  header: string;
  render: (row: T) => ComponentChild;
  /** Right-aligns a column, for amounts. */
  numeric?: boolean;
}

export interface DataTableProps<T> {
  /** Screen-reader caption describing what the grid holds. */
  caption: string;
  columns: Array<Column<T>>;
  rows: T[];
  rowId: (row: T) => number;
  /** Spoken name for a row, used as the selection checkbox's label. */
  rowLabel: (row: T) => string;
  emptyMessage: string;
  selectable?: boolean;
  selection?: ReadonlySet<number>;
  onToggleRow?: (id: number) => void;
}

export function DataTable<T>({
  caption,
  columns,
  rows,
  rowId,
  rowLabel,
  emptyMessage,
  selectable = false,
  selection,
  onToggleRow,
}: DataTableProps<T>) {
  const t = useTranslation();

  if (rows.length === 0) {
    return (
      <p class="vm-card text-muted" data-testid="grid-empty">
        {emptyMessage}
      </p>
    );
  }

  return (
    <div class="overflow-x-auto rounded-lg border border-border">
      <table class="w-full border-collapse text-sm">
        <caption class="sr-only">{caption}</caption>
        <thead>
          <tr class="bg-surface text-left text-muted">
            {selectable ? (
              <th scope="col" class="w-10 px-3 py-2">
                <span class="sr-only">{t("select_row", { name: "" })}</span>
              </th>
            ) : null}
            {columns.map((column) => (
              <th
                key={column.key}
                scope="col"
                class={`px-3 py-2 font-semibold ${column.numeric === true ? "text-right" : ""}`}
              >
                {column.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const id = rowId(row);
            const checked = selection?.has(id) ?? false;
            return (
              <tr
                key={id}
                class={`border-t border-border ${checked ? "bg-selected" : ""}`}
                data-selected={checked ? "true" : undefined}
                onClick={
                  selectable && onToggleRow !== undefined
                    ? () => onToggleRow(id)
                    : undefined
                }
              >
                {selectable ? (
                  <td class="px-3 py-2">
                    <input
                      type="checkbox"
                      checked={checked}
                      aria-label={t("select_row", { name: rowLabel(row) })}
                      onClick={(event) => event.stopPropagation()}
                      onChange={() => onToggleRow?.(id)}
                    />
                  </td>
                ) : null}
                {columns.map((column) => (
                  <td
                    key={column.key}
                    class={`px-3 py-2 ${column.numeric === true ? "text-right tabular-nums" : ""}`}
                  >
                    {column.render(row)}
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

/**
 * A concept or user name with the faint "(deleted)" tag.
 *
 * BACKEND.md § 1.2: the tag marks a state and is not part of the name, so it is
 * rendered as a separate node with reduced weight rather than concatenated.
 */
export function DeletedAwareName({ name, deleted }: { name: string; deleted: boolean }) {
  const t = useTranslation();
  return (
    <span>
      {name}
      {deleted ? <span class="vm-tag-deleted">{t("deleted_tag")}</span> : null}
    </span>
  );
}

/** An In/Out marker that does not rely on colour alone. */
export function FlowBadge({ flow }: { flow: "in" | "out" }) {
  const t = useTranslation();
  const isIn = flow === "in";
  return (
    <span
      class={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium ${
        isIn ? "border-positive text-positive" : "border-negative text-negative"
      }`}
    >
      <span aria-hidden="true">{isIn ? "↓" : "↑"}</span>
      {isIn ? t("flow_in") : t("flow_out")}
    </span>
  );
}
