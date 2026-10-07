/**
 * Start an export (0.9 J1u, J27.6). From a collection the dialog is prefilled with what the page
 * shows: its type, its data context, its filters and its parent scope; the search is not carried
 * (D60). From Settings › Jobs it starts empty, with a workspace to choose (D57). The export runs in
 * the background; the notifications follow it (`JobNotifications`).
 */

import { useEffect, useMemo, useState } from "react";
import { api } from "@/api/client";
import { errorMessage, isApiError } from "@/api/errors";
import type {
  CollectionFilter,
  EngineModel,
  ExportFormat,
  ExportRelations,
  ExportRequest,
  Job,
  Workspace,
} from "@/types";
import { Choice } from "@/ui/Choice";
import { FormField } from "@/ui/FormField";
import { Modal } from "@/ui/Modal";
import { MultiSelect } from "@/ui/MultiSelect";
import { Notice } from "@/ui/Notice";
import { criteriaFromFilters, exportField, exportableTypes, type ExportField } from "./exportRequest";

export interface ExportStart {
  /** The workspace; none lets the user choose one. */
  workspaceKey?: string;
  changeSetId?: string;
  publicationId?: string;
  /** The types offered, in the model's order, and those chosen at first. */
  objectTypeKeys: readonly string[];
  selected: readonly string[];
  /** The collection's filters, for its type. */
  filters?: { objectTypeKey: string; filters: CollectionFilter[] };
  search?: string;
  /** The page's parent scope: records directly below this record, of the filtered type. */
  parentObjectId?: string;
}

const RELATIONS: readonly (readonly [ExportRelations, string])[] = [
  ["withinScope", "Between exported records"],
  ["all", "All their relationships"],
  ["none", "None"],
];

const FORMATS: readonly (readonly [ExportFormat, string])[] = [
  ["xlsx", "Excel (XLSX)"],
  ["csv", "CSV"],
  ["jsonl", "JSON Lines"],
];

export function ExportDialog({
  model,
  start,
  onClose,
  onStarted,
}: {
  model: EngineModel;
  start: ExportStart;
  onClose: () => void;
  onStarted: (job: Job) => void;
}) {
  const types = useMemo(() => exportableTypes(model, start.objectTypeKeys), [model, start.objectTypeKeys]);
  const [workspaceKey, setWorkspaceKey] = useState(start.workspaceKey ?? "");
  const [workspaces, setWorkspaces] = useState<Workspace[]>();
  const [chosen, setChosen] = useState<string[]>([...start.selected]);
  const [belowParent, setBelowParent] = useState(Boolean(start.parentObjectId));
  const [asOf, setAsOf] = useState("");
  const [relations, setRelations] = useState<ExportRelations>("withinScope");
  const [format, setFormat] = useState<ExportFormat>("xlsx");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<{ field: ExportField; message: string }>();

  useEffect(() => {
    if (start.workspaceKey) return;
    let current = true;
    api
      .workspaces()
      .then((page) => {
        if (!current) return;
        setWorkspaces(page.items);
        setWorkspaceKey((key) => key || page.items[0]?.key || "");
      })
      .catch((cause) => current && setError({ field: "form", message: errorMessage(cause) }));
    return () => {
      current = false;
    };
  }, [start.workspaceKey]);

  const dated = types.some((type) => chosen.includes(type.key) && type.effectivePeriod);
  const filtered = start.filters && chosen.includes(start.filters.objectTypeKey) ? start.filters : undefined;
  // The page's scope is a criterion on its own type, as the page reads it: direct children only.
  const scoped = filtered && start.parentObjectId && belowParent ? start.parentObjectId : undefined;
  const context = start.changeSetId ? "the change set" : start.publicationId ? "the publication" : "live data";

  async function submit() {
    const body: ExportRequest = {
      workspaceKey,
      context: { changeSetId: start.changeSetId ?? null, publicationId: start.publicationId ?? null },
      scope: {
        types: types
          .filter((type) => chosen.includes(type.key))
          .map((type) => ({
            objectTypeKey: type.key,
            where:
              filtered?.objectTypeKey === type.key
                ? [
                    ...criteriaFromFilters(model, filtered.filters),
                    ...(scoped ? [{ field: "parentObjectId", op: "eq", value: scoped }] : []),
                  ]
                : [],
          })),
        parentObjectId: null,
        asOf: dated && asOf ? asOf : null,
      },
      include: { relations },
      format,
    };
    setPending(true);
    setError(undefined);
    try {
      onStarted(await api.createExport(body));
    } catch (cause) {
      const pointer = isApiError(cause) ? (cause.details as { path?: unknown } | undefined)?.path : undefined;
      setError({ field: exportField(pointer), message: errorMessage(cause) });
    } finally {
      setPending(false);
    }
  }

  const fieldError = (field: ExportField) => (error?.field === field ? error.message : undefined);

  return (
    <Modal title="Export" size="wide" busy={pending} onClose={onClose}>
      <form
        className="dialog-form"
        onSubmit={(event) => {
          event.preventDefault();
          void submit();
        }}
      >
        <section className="dialog-form-section" aria-labelledby="export-what">
          <h3 id="export-what">What to export</h3>
          {!start.workspaceKey && (
            <FormField label="Workspace">
              {(control) => (
                <select
                  {...control}
                  value={workspaceKey}
                  disabled={!workspaces}
                  onChange={(event) => setWorkspaceKey(event.target.value)}
                >
                  {(workspaces ?? []).map((workspace) => (
                    <option key={workspace.key} value={workspace.key}>
                      {workspace.label}
                    </option>
                  ))}
                </select>
              )}
            </FormField>
          )}
          <FormField
            label="Record types"
            help={`Read from ${context}${start.workspaceKey ? ` in workspace “${start.workspaceKey}”` : ""}, all at one instant.`}
            error={fieldError("types")}
          >
            {(control) => (
              <MultiSelect
                label="Record types"
                describedBy={control["aria-describedby"]}
                options={types.map((type) => ({ id: type.key, label: type.pluralName }))}
                selected={chosen}
                onChange={setChosen}
                addLabel="Add a type"
                emptyLabel="No type chosen yet."
              />
            )}
          </FormField>
          {filtered && filtered.filters.length > 0 && (
            <p className="admin-hint">
              {model.objectTypes.find((type) => type.key === filtered.objectTypeKey)?.pluralName} are exported with this
              page's {filtered.filters.length === 1 ? "filter" : `${filtered.filters.length} filters`}.
            </p>
          )}
          {start.search && (
            <Notice tone="info">
              The page's search “{start.search}” is not applied: an export selects records by filters only.
            </Notice>
          )}
          {start.parentObjectId && filtered && (
            <FormField label="Where" error={fieldError("scope")} group>
              {() => (
                <label className="checkbox">
                  <input
                    type="checkbox"
                    checked={belowParent}
                    onChange={(event) => setBelowParent(event.target.checked)}
                  />
                  Only the{" "}
                  {model.objectTypes.find((type) => type.key === filtered.objectTypeKey)?.pluralName.toLowerCase()} this
                  page is narrowed to
                </label>
              )}
            </FormField>
          )}
          {dated && (
            <FormField
              label="Valid on"
              help="Types with a validity period export the records valid on this date; the others are exported as they are. Leave empty for all."
              error={fieldError("asOf")}
            >
              {(control) => (
                <input {...control} type="date" value={asOf} onChange={(event) => setAsOf(event.target.value)} />
              )}
            </FormField>
          )}
        </section>

        <section className="dialog-form-section" aria-labelledby="export-file">
          <h3 id="export-file">The file</h3>
          <FormField label="Relationships" group>
            {() => <Choice name="export-relations" value={relations} options={RELATIONS} onChange={setRelations} />}
          </FormField>
          <FormField label="Format" group>
            {() => <Choice name="export-format" value={format} options={FORMATS} onChange={setFormat} />}
          </FormField>
        </section>

        {error?.field === "form" && (
          <Notice tone="error" title="The export was not started">
            {error.message}
          </Notice>
        )}
        <div className="dialog-actions">
          <button type="button" className="secondary" disabled={pending} onClick={onClose}>
            Cancel
          </button>
          <button className="primary" disabled={pending || !chosen.length || !workspaceKey}>
            {pending ? "Starting…" : "Start export"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
