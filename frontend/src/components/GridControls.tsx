/**
 * Grid toolbar pieces: search box and pagination.
 *
 * FRONTEND.md appendix: every grid is searchable and record grids are paginated
 * with a selectable page size of 10, 20, 50 or the full list.
 */
import type { JSX } from "preact";

import { useTranslation } from "@/hooks/useTranslation";
import type { PageSize } from "@/types/api";

export interface SearchBoxProps {
  value: string;
  onChange: (value: string) => void;
  label?: string;
}

/** A labelled substring filter. Filtering happens server-side for record grids. */
export function SearchBox({ value, onChange, label }: SearchBoxProps) {
  const t = useTranslation();
  return (
    <div class="flex items-center gap-2">
      <label class="vm-label mb-0 whitespace-nowrap" for="grid-search">
        {label ?? t("search")}
      </label>
      <input
        id="grid-search"
        class="vm-input"
        type="search"
        value={value}
        placeholder={t("search_placeholder")}
        onInput={(event: JSX.TargetedEvent<HTMLInputElement>) =>
          onChange(event.currentTarget.value)
        }
      />
    </div>
  );
}

export interface PaginationProps {
  page: number;
  size: PageSize;
  meta: { page: number; per_page: number; total: number; total_pages: number } | null;
  onPageChange: (page: number) => void;
  onSizeChange: (size: PageSize) => void;
}

const SIZES: Array<{ value: PageSize; labelKey: "pagination_all" | null }> = [
  { value: 10, labelKey: null },
  { value: 20, labelKey: null },
  { value: 50, labelKey: null },
  { value: "all", labelKey: "pagination_all" },
];

/** Page-size selector plus previous/next controls. */
export function Pagination({
  page,
  size,
  meta,
  onPageChange,
  onSizeChange,
}: PaginationProps) {
  const t = useTranslation();
  const totalPages = meta?.total_pages ?? 1;
  const isAll = size === "all";

  return (
    <div class="mt-3 flex flex-wrap items-center justify-between gap-3 text-sm">
      <p class="text-muted" aria-live="polite">
        {t("page_label", { page: isAll ? 1 : page, total: totalPages })}
      </p>
      <div class="flex items-center gap-2">
        <label class="vm-label mb-0" for="page-size">
          {t("rows_per_page")}
        </label>
        <select
          id="page-size"
          class="vm-input w-auto"
          value={String(size)}
          onChange={(event: JSX.TargetedEvent<HTMLSelectElement>) => {
            const raw = event.currentTarget.value;
            onSizeChange(raw === "all" ? "all" : (Number(raw) as PageSize));
          }}
        >
          {SIZES.map((option) => (
            <option key={String(option.value)} value={String(option.value)}>
              {option.labelKey === null ? String(option.value) : t(option.labelKey)}
            </option>
          ))}
        </select>
        <button
          type="button"
          class="vm-button"
          onClick={() => onPageChange(page - 1)}
          disabled={isAll || page <= 1}
          aria-label={t("pagination_previous")}
        >
          ‹
        </button>
        <button
          type="button"
          class="vm-button"
          onClick={() => onPageChange(page + 1)}
          disabled={isAll || page >= totalPages}
          aria-label={t("pagination_next")}
        >
          ›
        </button>
      </div>
    </div>
  );
}
