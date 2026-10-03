/**
 * Concepts screen (FRONTEND.md § 3, API_SURFACE.md § 3.3).
 *
 * The list is a small unpaginated reference set, so search and paging happen in
 * the browser. Renaming and deleting are both gated by a confirmation, because a
 * rename applies to every record that references the concept and a delete makes
 * its budgets and working-month records disappear.
 */
import { useState } from "preact/hooks";

import { ConfirmDialog } from "./ConfirmDialog";
import { DataTable, DeletedAwareName, FlowBadge, type Column } from "./DataTable";
import { ErrorNotice, LoadingNotice } from "./ErrorNotice";
import { Field, SelectField } from "./Field";
import { Modal } from "./Modal";
import { SearchBox } from "./GridControls";
import {
  useAllConcepts,
  useBulkDeleteConcepts,
  useConcepts,
  useCreateConcept,
  useDeleteConcept,
  useRenameConcept,
} from "@/hooks/useConcepts";
import { useTranslation } from "@/hooks/useTranslation";
import type { Concept, Flow } from "@/types/api";
import { validateConceptName, validateRequired, type Verdict } from "@/utils/validation";

export function ConceptsScreen() {
  const t = useTranslation();
  const [showDeleted, setShowDeleted] = useState(false);
  const [search, setSearch] = useState("");
  const [selection, setSelection] = useState<ReadonlySet<number>>(new Set<number>());
  const [addOpen, setAddOpen] = useState(false);
  const [renaming, setRenaming] = useState<Concept | null>(null);
  const [deleting, setDeleting] = useState<Concept | null>(null);
  const [confirmBulk, setConfirmBulk] = useState(false);

  const live = useConcepts();
  const all = useAllConcepts(showDeleted);
  const source = showDeleted ? all : live;
  const createConcept = useCreateConcept();
  const renameConcept = useRenameConcept();
  const deleteConcept = useDeleteConcept();
  const bulkDelete = useBulkDeleteConcepts();

  const needle = search.trim().toLowerCase();
  const rows = (source.data?.data ?? []).filter(
    (concept) => needle === "" || concept.name.toLowerCase().includes(needle),
  );

  const columns: Array<Column<Concept>> = [
    {
      key: "created",
      header: t("concept_created_column"),
      render: (concept) => <time dateTime={concept.created_at}>{concept.created_at.slice(0, 10)}</time>,
    },
    {
      key: "name",
      header: t("concept_column"),
      render: (concept) => (
        <DeletedAwareName name={concept.name} deleted={concept.is_deleted} />
      ),
    },
    { key: "flow", header: t("flow_column"), render: (concept) => <FlowBadge flow={concept.flow} /> },
    {
      key: "user",
      header: t("user_column"),
      render: (concept) => (
        <DeletedAwareName
          name={concept.created_by ?? ""}
          deleted={concept.created_by_is_deleted}
        />
      ),
    },
    {
      key: "actions",
      header: t("edit"),
      render: (concept) =>
        concept.is_deleted ? null : (
          <span class="flex gap-1">
            <button
              type="button"
              class="vm-button"
              onClick={() => setRenaming(concept)}
              data-testid={`rename-${concept.id}`}
            >
              {t("edit")}
            </button>
            <button
              type="button"
              class="vm-button-danger"
              onClick={() => setDeleting(concept)}
              data-testid={`delete-${concept.id}`}
            >
              {t("delete")}
            </button>
          </span>
        ),
    },
  ];

  return (
    <div class="space-y-4">
      <header class="flex flex-wrap items-center justify-between gap-3">
        <h2 class="text-lg font-semibold">{t("concepts_title")}</h2>
        <div class="flex flex-wrap items-center gap-3">
          <label class="flex items-center gap-2 text-sm text-muted">
            <input
              type="checkbox"
              checked={showDeleted}
              data-testid="show-deleted"
              onChange={(event) => setShowDeleted(event.currentTarget.checked)}
            />
            {t("show_deleted")}
          </label>
          <button
            type="button"
            class="vm-button-primary"
            onClick={() => setAddOpen(true)}
            data-testid="add-concept"
          >
            {t("add_concept")}
          </button>
          <button
            type="button"
            class="vm-button-danger"
            onClick={() => setConfirmBulk(true)}
            disabled={selection.size === 0}
            data-testid="delete-concepts"
          >
            {t("delete_records_count", { count: selection.size })}
          </button>
        </div>
      </header>

      <SearchBox value={search} onChange={setSearch} />

      {source.isPending ? <LoadingNotice label={t("loading")} /> : null}
      {source.error === null ? null : <ErrorNotice error={source.error} />}

      <DataTable
        caption={t("concepts_title")}
        columns={columns}
        rows={rows}
        rowId={(concept) => concept.id}
        rowLabel={(concept) => concept.name}
        emptyMessage={t("no_results")}
        selectable
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

      {addOpen ? (
        <AddConceptDialog
          busy={createConcept.isPending}
          error={createConcept.error}
          onCancel={() => setAddOpen(false)}
          onSubmit={(name, flow) => {
            createConcept.mutate(
              { name, flow },
              { onSuccess: () => setAddOpen(false) },
            );
          }}
        />
      ) : null}

      {renaming === null ? null : (
        <RenameConceptDialog
          concept={renaming}
          busy={renameConcept.isPending}
          error={renameConcept.error}
          onCancel={() => setRenaming(null)}
          onSubmit={(name) => {
            renameConcept.mutate(
              { id: renaming.id, name },
              { onSuccess: () => setRenaming(null) },
            );
          }}
        />
      )}

      {deleting === null ? null : (
        <ConfirmDialog
          title={t("delete_concept_warning_title")}
          body={t("delete_concept_warning_body")}
          confirmLabel={t("delete")}
          destructive
          busy={deleteConcept.isPending}
          onCancel={() => setDeleting(null)}
          onConfirm={() => {
            deleteConcept.mutate(deleting.id, { onSuccess: () => setDeleting(null) });
          }}
        />
      )}

      {confirmBulk ? (
        <ConfirmDialog
          title={t("delete_concept_warning_title")}
          body={t("delete_concept_warning_body")}
          confirmLabel={t("delete_records_count", { count: selection.size })}
          destructive
          busy={bulkDelete.isPending}
          onCancel={() => setConfirmBulk(false)}
          onConfirm={() => {
            bulkDelete.mutate([...selection], {
              onSuccess: () => {
                setSelection(new Set<number>());
                setConfirmBulk(false);
              },
            });
          }}
        />
      ) : null}
    </div>
  );
}

interface AddConceptDialogProps {
  busy: boolean;
  error: unknown;
  onCancel: () => void;
  onSubmit: (name: string, flow: Flow) => void;
}

function AddConceptDialog({ busy, error, onCancel, onSubmit }: AddConceptDialogProps) {
  const t = useTranslation();
  const [name, setName] = useState("");
  const [flow, setFlow] = useState<Flow>("out");
  const [verdict, setVerdict] = useState<Verdict>(null);

  return (
    <Modal
      title={t("add_concept")}
      onClose={onCancel}
      footer={
        <>
          <button type="button" class="vm-button" onClick={onCancel} disabled={busy}>
            {t("cancel")}
          </button>
          <button
            type="button"
            class="vm-button-primary"
            disabled={busy}
            data-testid="submit-concept"
            onClick={() => {
              const checked = validateConceptName(name);
              setVerdict(checked);
              if (checked === null) {
                onSubmit(name.trim(), flow);
              }
            }}
          >
            {busy ? t("loading") : t("save")}
          </button>
        </>
      }
    >
      {error === null ? null : <ErrorNotice error={error} />}
      <Field
        label={t("concept_name_label")}
        value={name}
        error={verdict}
        required
        onInput={setName}
      />
      <SelectField
        label={t("concept_flow_label")}
        value={flow}
        onChange={(value) => setFlow(value === "in" ? "in" : "out")}
        options={[
          { value: "out", label: t("flow_out") },
          { value: "in", label: t("flow_in") },
        ]}
      />
    </Modal>
  );
}

interface RenameConceptDialogProps {
  concept: Concept;
  busy: boolean;
  error: unknown;
  onCancel: () => void;
  onSubmit: (name: string) => void;
}

/**
 * Rename, behind the confirmation FRONTEND.md § 3 requires.
 *
 * Flow is shown but disabled: it is immutable, and the only way to change it is
 * to delete the concept and create a new one (BACKEND.md § 5.2).
 */
function RenameConceptDialog({
  concept,
  busy,
  error,
  onCancel,
  onSubmit,
}: RenameConceptDialogProps) {
  const t = useTranslation();
  const [name, setName] = useState(concept.name);
  const [verdict, setVerdict] = useState<Verdict>(null);
  const [confirmed, setConfirmed] = useState(false);

  if (!confirmed) {
    return (
      <ConfirmDialog
        title={t("rename_warning_title")}
        body={t("rename_warning_body")}
        confirmLabel={t("confirm")}
        onCancel={onCancel}
        onConfirm={() => setConfirmed(true)}
      />
    );
  }

  return (
    <Modal
      title={t("edit_concept")}
      onClose={onCancel}
      footer={
        <>
          <button type="button" class="vm-button" onClick={onCancel} disabled={busy}>
            {t("cancel")}
          </button>
          <button
            type="button"
            class="vm-button-primary"
            disabled={busy}
            data-testid="submit-rename"
            onClick={() => {
              const checked =
                validateRequired(name) ?? validateConceptName(name);
              setVerdict(checked);
              if (checked === null) {
                onSubmit(name.trim());
              }
            }}
          >
            {busy ? t("loading") : t("save")}
          </button>
        </>
      }
    >
      {error === null ? null : <ErrorNotice error={error} />}
      <Field
        label={t("concept_name_label")}
        value={name}
        error={verdict}
        required
        onInput={setName}
      />
      <p class="text-sm text-muted">{t("flow_immutable_note")}</p>
    </Modal>
  );
}
