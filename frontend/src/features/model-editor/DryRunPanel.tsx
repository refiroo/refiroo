/**
 * The draft's dry run in the editor's drawer (0.10 A5b, D79): after each step that can change the
 * load, the whole file checked against the draft's model, writing nothing (A3, D67). Per source,
 * the records created, updated and unchanged, the values, relationships and related records, the
 * rows refused by code, each with what it was before the step; each figure opens its rows.
 */

import { api } from "@/api/client";
import type { DryRun, DryRunSource, JobRow, ModelDraftOutline } from "@/types";
import { formatServerTime } from "@/lib/dates";
import { EmptyState } from "@/ui/EmptyState";
import { InlineError } from "@/ui/InlineError";
import { Modal } from "@/ui/Modal";
import { Notice } from "@/ui/Notice";
import { StatusPill } from "@/ui/StatusPill";
import { JobRowsTable } from "@/features/jobs/ImportOutcome";
import { typeName } from "@/features/model-editor/outline";

/** The rows behind a figure: a source's, by status or refusal code. */
export interface DryRunRows {
  source: number;
  status: JobRow["status"];
  code?: string;
  title: string;
}

interface Figure {
  name: string;
  label: string;
  now: number;
  rows?: Omit<DryRunRows, "title">;
  refused?: boolean;
}

function figuresOf(source: DryRunSource): Figure[] {
  const applied = { source: source.source, status: "applied" as const };
  return [
    { name: "records.created", label: "created", now: source.records.created, rows: applied },
    { name: "records.updated", label: "updated", now: source.records.updated, rows: applied },
    { name: "records.unchanged", label: "unchanged", now: source.records.unchanged, rows: applied },
    { name: "values", label: "values", now: source.values, rows: applied },
    { name: "relationships", label: "relationships", now: source.relationships, rows: applied },
    { name: "relatedRecords", label: "related records created", now: source.relatedRecords, rows: applied },
    // Rows skipped for want of a key (0.10 A7, D110) make no item, so no rows stand behind the figure.
    { name: "skippedRows", label: "rows skipped, no key", now: source.skippedRows ?? 0 },
    ...source.rejections.map((item) => ({
      name: `rejections.${item.code}`,
      label: `rows refused · ${item.code}`,
      now: item.rows,
      refused: true,
      rows: { source: source.source, status: "rejected" as const, code: item.code },
    })),
  ];
}

/** In words for the drawer's toggle: "checking", "checked, 0 refused". */
export function dryRunLabel(dryRun: DryRun | undefined): string {
  if (!dryRun) return "Not run yet";
  if (dryRun.state === "checking") return "Checking…";
  if (dryRun.state !== "completed" || !dryRun.summary) return dryRun.state === "failed" ? "Failed" : "Stopped";
  const refused = dryRun.summary.sources.reduce(
    (total, source) => total + source.rejections.reduce((sum, item) => sum + item.rows, 0),
    0,
  );
  return `Checked, ${refused} refused`;
}

export function DryRunPanel({
  dryRun,
  error,
  outline,
  onRows,
  onRetry,
}: {
  dryRun: DryRun | undefined;
  error: string;
  outline: ModelDraftOutline;
  onRows: (rows: DryRunRows) => void;
  onRetry: () => void;
}) {
  if (error) return <InlineError message={error} onRetry={onRetry} />;
  if (!dryRun)
    return (
      <EmptyState>
        No dry run yet. Once a column is mapped, each step checks the whole file against the draft, writing nothing.
      </EmptyState>
    );
  const summary = dryRun.summary;
  const was = (source: DryRunSource, name: string) =>
    summary?.difference?.find((item) => item.objectTypeKey === source.objectTypeKey && item.sheet === source.sheet)
      ?.figures[name]?.was;
  return (
    <div className="dry-run" aria-busy={dryRun.state === "checking"}>
      <p className="dry-run-head" role="status">
        {dryRun.state === "checking" ? (
          <StatusPill tone="neutral">Checking the whole file…</StatusPill>
        ) : dryRun.state === "completed" ? (
          <StatusPill tone="success">Checked</StatusPill>
        ) : (
          <StatusPill tone="warning">{dryRun.state === "failed" ? "Failed" : "Stopped"}</StatusPill>
        )}
        <span className="muted">
          {summary
            ? `Draft version ${dryRun.draftVersion} · ${summary.rows.total.toLocaleString()} rows of its sources, all checked · nothing written · ${formatServerTime(summary.ranAt)}`
            : `Draft version ${dryRun.draftVersion}`}
        </span>
      </p>
      {dryRun.state === "failed" && dryRun.error && <Notice tone="error">{dryRun.error.message}</Notice>}
      {summary?.sources.map((source) => (
        <section
          key={source.source}
          className="dry-run-source"
          aria-label={`${typeName(outline, source.objectTypeKey)} from ${source.sheet}`}
        >
          <h3 className="dry-run-source-title">
            {typeName(outline, source.objectTypeKey)}{" "}
            <span className="muted">
              from {source.sheet} · {source.rows} rows
            </span>
          </h3>
          <div className="dry-run-figures">
            {figuresOf(source)
              .filter(
                (figure) =>
                  figure.now > 0 || was(source, figure.name) !== undefined || figure.name === "records.created",
              )
              .map((figure) => {
                const before = was(source, figure.name);
                const title = `${typeName(outline, source.objectTypeKey)}: ${figure.now} ${figure.label}`;
                return (
                  <button
                    key={figure.name}
                    type="button"
                    className={`dry-run-figure${figure.refused ? " refused" : ""}`}
                    disabled={!figure.rows}
                    onClick={() => figure.rows && onRows({ ...figure.rows, title })}
                  >
                    <strong>{figure.now.toLocaleString()}</strong>
                    <span>{figure.label}</span>
                    {before !== undefined && <span className="muted">was {before.toLocaleString()}</span>}
                  </button>
                );
              })}
          </div>
        </section>
      ))}
      {summary && <p className="muted">Each figure opens the rows behind it.</p>}
    </div>
  );
}

/** The latest dry run's rows behind a figure, as an import's rows are shown. */
export function DryRunRowsDialog({
  draftId,
  rows: opened,
  onClose,
}: {
  draftId: string;
  rows: DryRunRows;
  onClose: () => void;
}) {
  return (
    <Modal
      title={opened.title}
      eyebrow="Dry run"
      description="Nothing was written: this is what loading would do."
      size="wide"
      onClose={onClose}
    >
      <div className="dialog-body">
        <JobRowsTable
          name="dry-run-rows"
          preview
          initialFilter={opened.status}
          deps={[draftId, opened.source, opened.code]}
          rows={(query) => api.modelDraftDryRunRows(draftId, { ...query, source: opened.source, code: opened.code })}
        />
      </div>
    </Modal>
  );
}
