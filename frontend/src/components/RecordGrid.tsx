/**
 * The record grid shared by Home, Budget and History.
 *
 * FRONTEND.md describes the same grid — Date, Concept, Amount, Flow, User — on
 * all three screens, with the same add/edit/delete actions and the same
 * search-plus-page-size controls. The differences are props: which record type,
 * which month, whether it is read only, and how the date column is displayed.
 *
 * Editing happens inline, in the row, as FRONTEND.md § 1.3.2 specifies. Adding
 * happens in a modal, because a new row does not exist yet.
 */
import type { ComponentChildren, JSX } from "preact";
import { useState } from "preact/hooks";

import { ConfirmDialog } from "./ConfirmDialog";
import { DataTable, DeletedAwareName, FlowBadge, type Column } from "./DataTable";
import { ErrorNotice, LoadingNotice } from "./ErrorNotice";
import { Field, SelectField } from "./Field";
import { Pagination, SearchBox } from "./GridControls";
import { Modal } from "./Modal";
import { useConcepts } from "@/hooks/useConcepts";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import { useTranslation } from "@/hooks/useTranslation";
import {
  selectedIds,
  useBulkDeleteRecords,
  useCreateRecord,
  useRecords,
  useUpdateRecord,
} from "@/hooks/useRecords";
import type { TranslationKey } from "@/l10n";
import type { Concept, MoneyRecord, PageSize, RecordType } from "@/types/api";
import { formatNullableAmount } from "@/utils/format";
import { validateAmount, validateDate, type Verdict } from "@/utils/validation";

export interface RecordGridProps {
  type: RecordType;
  /** Month to query. Required for transactions; ignored by the backend for budgets. */
  month?: string;
  /** History is read only: no selection, no add, no edit. */
  readOnly?: boolean;
  /** Display transform for the date column. Budget clamps into the working month. */
  displayDate?: (isoDate: string) => string;
  /** Default date offered by the add form. */
  defaultDate: string;
  caption: string;
  /** Extra toolbar content, e.g. the "Switch to current month" button. */
  toolbar?: ComponentChildren;
}

interface Draft {
  date: string;
  conceptId: string;
  amount: string;
}

interface DraftErrors {
  date: Verdict;
  concept: Verdict;
  amount: Verdict;
}

const NO_ERRORS: DraftErrors = { date: null, concept: null, amount: null };

function draftFrom(record: MoneyRecord): Draft {
  return {
    date: record.date,
    conceptId: String(record.concept_id),
    amount: record.amount === null ? "" : String(record.amount),
  };
}

function validateDraft(draft: Draft, isBudget: boolean): DraftErrors {
  return {
    date: validateDate(draft.date),
    concept: draft.conceptId === "" ? "validation_required" : null,
    amount: validateAmount(draft.amount, !isBudget),
  };
}

function isClean(errors: DraftErrors): boolean {
  return errors.date === null && errors.concept === null && errors.amount === null;
}

export function RecordGrid({
  type,
  month,
  readOnly = false,
  displayDate,
  defaultDate,
  caption,
  toolbar,
}: RecordGridProps) {
  const t = useTranslation();
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebouncedValue(search, 300);
  const [page, setPage] = useState(1);
  const [size, setSize] = useState<PageSize>(10);
  const [selection, setSelection] = useState<ReadonlySet<number>>(new Set<number>());
  const [addOpen, setAddOpen] = useState(false);
  const [confirmBulk, setConfirmBulk] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [draft, setDraft] = useState<Draft>({ date: "", conceptId: "", amount: "" });
  const [errors, setErrors] = useState<DraftErrors>(NO_ERRORS);

  const isBudget = type === "budget";
  const query = useRecords(
    { type, month, page, size, search: debouncedSearch },
    month !== undefined || isBudget,
  );
  const concepts = useConcepts();
  const createRecord = useCreateRecord();
  const updateRecord = useUpdateRecord();
  const bulkDelete = useBulkDeleteRecords();

  const rows = query.data?.data ?? [];
  const conceptList = concepts.data?.data ?? [];
  const showDate = displayDate ?? ((value: string) => value);

  const startEdit = (record: MoneyRecord): void => {
    setEditingId(record.id);
    setDraft(draftFrom(record));
    setErrors(NO_ERRORS);
  };

  const cancelEdit = (): void => {
    setEditingId(null);
    setErrors(NO_ERRORS);
  };

  const commitEdit = (): void => {
    const checked = validateDraft(draft, isBudget);
    setErrors(checked);
    if (!isClean(checked) || editingId === null) {
      return;
    }
    updateRecord.mutate(
      {
        id: editingId,
        type,
        patch: {
          date: draft.date,
          concept_id: Number(draft.conceptId),
          amount: draft.amount === "" ? null : draft.amount,
        },
      },
      { onSuccess: cancelEdit },
    );
  };

  const columns = buildColumns({
    t,
    rows: conceptList,
    isBudget,
    showDate,
    editingId,
    draft,
    errors,
    readOnly,
    onDraftChange: setDraft,
    onStartEdit: startEdit,
    onCancelEdit: cancelEdit,
    onCommitEdit: commitEdit,
    busy: updateRecord.isPending,
  });

  return (
    <section>
      <div class="mb-3 flex flex-wrap items-end justify-between gap-3">
        <div class="min-w-56 flex-1">
          <SearchBox value={search} onChange={setSearch} />
        </div>
        <div class="flex flex-wrap items-center gap-2">
          {toolbar}
          {readOnly ? null : (
            <>
              <button
                type="button"
                class="vm-button-primary"
                onClick={() => setAddOpen(true)}
                data-testid="add-record"
              >
                {t("add_record")}
              </button>
              <button
                type="button"
                class="vm-button-danger"
                onClick={() => setConfirmBulk(true)}
                disabled={selection.size === 0}
                data-testid="delete-selected"
              >
                {t("delete_records_count", { count: selection.size })}
              </button>
            </>
          )}
        </div>
      </div>

      {updateRecord.error === null ? null : <ErrorNotice error={updateRecord.error} />}
      {query.isPending ? <LoadingNotice label={t("loading")} /> : null}
      {query.error === null ? null : (
        <ErrorNotice error={query.error} onRetry={() => void query.refetch()} />
      )}

      <DataTable
        caption={caption}
        columns={columns}
        rows={rows}
        rowId={(row) => row.id}
        rowLabel={(row) => row.concept_name}
        emptyMessage={t("no_results")}
        selectable={!readOnly}
        selection={selection}
        onToggleRow={(id) =>
          setSelection((current) => {
            const next = new Set(current);
            if (next.has(id)) {
              next.delete(id);
            } else {
              next.add(id);
            }
            return next;
          })
        }
      />

      <Pagination
        page={page}
        size={size}
        meta={query.data?.meta ?? null}
        onPageChange={setPage}
        onSizeChange={(next) => {
          setSize(next);
          setPage(1);
        }}
      />

      {addOpen ? (
        <AddRecordDialog
          type={type}
          defaultDate={defaultDate}
          concepts={conceptList}
          busy={createRecord.isPending}
          error={createRecord.error}
          onCancel={() => setAddOpen(false)}
          onSubmit={(next) => {
            createRecord.mutate(next, { onSuccess: () => setAddOpen(false) });
          }}
        />
      ) : null}

      {confirmBulk ? (
        <ConfirmDialog
          title={t("delete_record")}
          body={t("selection_hint")}
          confirmLabel={t("delete_records_count", { count: selection.size })}
          destructive
          busy={bulkDelete.isPending}
          onCancel={() => setConfirmBulk(false)}
          onConfirm={() => {
            bulkDelete.mutate(
              { ids: selectedIds(rows, selection), type },
              {
                onSuccess: () => {
                  setSelection(new Set<number>());
                  setConfirmBulk(false);
                },
              },
            );
          }}
        />
      ) : null}
    </section>
  );
}

/** An inline validation message, announced and linked to its input. */
function InlineError({ id, verdict }: { id: string; verdict: Verdict }) {
  const t = useTranslation();
  if (verdict === null) {
    return null;
  }
  return (
    <span id={id} class="vm-error block" role="alert">
      {t(verdict)}
    </span>
  );
}

interface ColumnContext {
  t: (key: TranslationKey, vars?: Record<string, string | number>) => string;
  rows: Concept[];
  isBudget: boolean;
  showDate: (value: string) => string;
  editingId: number | null;
  draft: Draft;
  errors: DraftErrors;
  readOnly: boolean;
  busy: boolean;
  onDraftChange: (next: Draft) => void;
  onStartEdit: (record: MoneyRecord) => void;
  onCancelEdit: () => void;
  onCommitEdit: () => void;
}

/**
 * Build the grid's columns.
 *
 * Extracted from the component so the inline-edit branching stays readable; a
 * column either shows the stored value or, for the row being edited, an input.
 */
function buildColumns(context: ColumnContext): Array<Column<MoneyRecord>> {
  const { t, editingId, draft, errors, readOnly } = context;
  const isEditing = (row: MoneyRecord): boolean => editingId === row.id;

  const columns: Array<Column<MoneyRecord>> = [
    {
      key: "date",
      header: t("date_column"),
      render: (row) =>
        isEditing(row) ? (
          <>
            <input
              class="vm-input"
              type="date"
              value={draft.date}
              aria-label={t("date_column")}
              aria-invalid={errors.date !== null}
              aria-describedby={errors.date === null ? undefined : `${row.id}-date-error`}
              onInput={(event: JSX.TargetedEvent<HTMLInputElement>) =>
                context.onDraftChange({ ...draft, date: event.currentTarget.value })
              }
            />
            <InlineError id={`${row.id}-date-error`} verdict={errors.date} />
          </>
        ) : (
          <time dateTime={row.date}>{context.showDate(row.date)}</time>
        ),
    },
    {
      key: "concept",
      header: t("concept_column"),
      render: (row) =>
        isEditing(row) ? (
          <>
            <select
              class="vm-input"
              value={draft.conceptId}
              aria-label={t("concept_column")}
              aria-invalid={errors.concept !== null}
              aria-describedby={
                errors.concept === null ? undefined : `${row.id}-concept-error`
              }
              onChange={(event: JSX.TargetedEvent<HTMLSelectElement>) =>
                context.onDraftChange({ ...draft, conceptId: event.currentTarget.value })
              }
            >
              {context.rows.map((concept) => (
                <option key={concept.id} value={String(concept.id)}>
                  {concept.name}
                </option>
              ))}
            </select>
            <InlineError id={`${row.id}-concept-error`} verdict={errors.concept} />
          </>
        ) : (
          <DeletedAwareName name={row.concept_name} deleted={row.concept_is_deleted} />
        ),
    },
    {
      key: "amount",
      header: t("amount_column"),
      numeric: true,
      render: (row) =>
        isEditing(row) ? (
          <>
            <input
              class="vm-input text-right"
              type="text"
              inputMode="decimal"
              value={draft.amount}
              aria-label={t("amount_column")}
              aria-invalid={errors.amount !== null}
              aria-describedby={
                errors.amount === null ? undefined : `${row.id}-amount-error`
              }
              onInput={(event: JSX.TargetedEvent<HTMLInputElement>) =>
                context.onDraftChange({ ...draft, amount: event.currentTarget.value })
              }
            />
            <InlineError id={`${row.id}-amount-error`} verdict={errors.amount} />
          </>
        ) : (
          formatNullableAmount(row.amount)
        ),
    },
    {
      key: "flow",
      header: t("flow_column"),
      render: (row) => {
        if (!isEditing(row)) {
          return <FlowBadge flow={row.concept_flow} />;
        }
        const chosen = context.rows.find(
          (concept) => String(concept.id) === draft.conceptId,
        );
        return chosen === undefined ? null : <FlowBadge flow={chosen.flow} />;
      },
    },
    {
      key: "user",
      header: t("user_column"),
      render: (row) => <DeletedAwareName name={row.username} deleted={row.user_is_deleted} />,
    },
  ];

  if (readOnly) {
    return columns;
  }

  columns.push({
    key: "actions",
    header: t("edit"),
    render: (row) =>
      isEditing(row) ? (
        <span class="flex gap-1">
          <button
            type="button"
            class="vm-button-primary"
            onClick={context.onCommitEdit}
            disabled={context.busy}
            data-testid={`save-${row.id}`}
          >
            {t("save")}
          </button>
          <button type="button" class="vm-button" onClick={context.onCancelEdit}>
            {t("cancel")}
          </button>
        </span>
      ) : (
        <button
          type="button"
          class="vm-button"
          onClick={() => context.onStartEdit(row)}
          data-testid={`edit-${row.id}`}
        >
          {t("edit")}
        </button>
      ),
  });

  return columns;
}

interface AddRecordDialogProps {
  type: RecordType;
  defaultDate: string;
  concepts: Concept[];
  busy: boolean;
  error: unknown;
  onCancel: () => void;
  onSubmit: (input: {
    type: RecordType;
    date: string;
    concept_id: number;
    amount: string | null;
  }) => void;
}

/**
 * The add-record modal.
 *
 * Flow is shown but never selectable: it is a property of the chosen concept,
 * and the backend ignores any flow sent in the body (BACKEND.md § 5.1).
 */
function AddRecordDialog({
  type,
  defaultDate,
  concepts,
  busy,
  error,
  onCancel,
  onSubmit,
}: AddRecordDialogProps) {
  const t = useTranslation();
  const isBudget = type === "budget";
  const [draft, setDraft] = useState<Draft>({
    date: defaultDate,
    conceptId: "",
    amount: "",
  });
  const [errors, setErrors] = useState<DraftErrors>(NO_ERRORS);
  const chosen = concepts.find((concept) => String(concept.id) === draft.conceptId);

  const submit = (): void => {
    const checked = validateDraft(draft, isBudget);
    setErrors(checked);
    if (!isClean(checked)) {
      return;
    }
    onSubmit({
      type,
      date: draft.date,
      concept_id: Number(draft.conceptId),
      amount: draft.amount === "" ? null : draft.amount,
    });
  };

  return (
    <Modal
      title={t("add_record")}
      onClose={onCancel}
      footer={
        <>
          <button type="button" class="vm-button" onClick={onCancel} disabled={busy}>
            {t("cancel")}
          </button>
          <button
            type="button"
            class="vm-button-primary"
            onClick={submit}
            disabled={busy}
            data-testid="submit-record"
          >
            {busy ? t("loading") : t("save")}
          </button>
        </>
      }
    >
      {error === null ? null : <ErrorNotice error={error} />}
      <Field
        label={t("date_column")}
        type="date"
        required
        value={draft.date}
        error={errors.date}
        onInput={(value) => setDraft({ ...draft, date: value })}
      />
      <SelectField
        label={t("concept_column")}
        value={draft.conceptId}
        error={errors.concept}
        onChange={(value) => setDraft({ ...draft, conceptId: value })}
        options={[
          { value: "", label: "—" },
          ...concepts.map((concept) => ({
            value: String(concept.id),
            label: `${concept.name} · ${
              concept.flow === "in" ? t("flow_in") : t("flow_out")
            }`,
          })),
        ]}
      />
      <p class="mb-3 text-sm text-muted" data-testid="flow-preview">
        {t("flow_column")}:{" "}
        {chosen === undefined ? "—" : <FlowBadge flow={chosen.flow} />}
      </p>
      <Field
        label={isBudget ? t("budget_amount_optional") : t("amount_column")}
        required={!isBudget}
        value={draft.amount}
        error={errors.amount}
        hint={isBudget ? t("budget_hint") : undefined}
        onInput={(value) => setDraft({ ...draft, amount: value })}
      />
    </Modal>
  );
}
