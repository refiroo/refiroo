/**
 * What an import's job page shows beside its state (0.9 J4, J27.13): the file and profile, the
 * preview (counts, the result under the chosen policy, whether it covered every item), after
 * loading the result and how to act on refused rows (D94), the binding report per source and
 * column (D86), and the file's rows with their outcomes, paged (D84). Names come from the model;
 * nothing names a type.
 */

import { useState } from "react";
import { api } from "@/api/client";
import { attributeName } from "@/model/fields";
import { useCursorWindow } from "@/lib/hooks/useCursorWindow";
import type { BindingReportColumn, EngineModel, ImportProfile, Job, JobItemOutcome, JobNotice, JobRow } from "@/types";
import { Choice } from "@/ui/Choice";
import { DataTable, type DataColumn } from "@/ui/DataTable";
import { DescriptionList, type DescriptionItem } from "@/ui/DescriptionList";
import { Notice } from "@/ui/Notice";
import { Section } from "@/ui/Section";
import { SettingsTable } from "@/ui/SettingsTable";
import { StatusPill } from "@/ui/StatusPill";
import { count } from "@/features/settings/limits";
import { keyless } from "./importRequest";
import { Verdict } from "./Verdict";
import { fileSize } from "./jobText";

const ROWS_PAGE = 50;

interface ImportParameters {
  policy?: "atomic" | "independent";
  onExisting?: "reject" | "overwrite";
  otherWorkspaceIds?: "refuse" | "counterparts";
  file?: { name: string; format: string; bytes: number };
  profile?: { key: string | null; version: number | null; definition?: Pick<ImportProfile, "sources"> } | null;
}

const parametersOf = (job: Job) => job.parameters as ImportParameters;

/** "Import of codes.csv", or "Import" before the file is known. */
export function importTitle(job: Job): string {
  const name = parametersOf(job).file?.name;
  return name ? `Import of ${name}` : "Import";
}

/** The preview's outcomes are the job's until it is confirmed; then the execution's replace them. */
const previewing = (job: Job) => !job.confirmedAt;

export function ImportFacts({ job }: { job: Job }) {
  const parameters = parametersOf(job);
  const items: DescriptionItem[] = [
    ...(parameters.file
      ? [{ term: "File", value: `${parameters.file.name} (${fileSize(parameters.file.bytes)})` }]
      : []),
    { term: "Profile", value: parameters.profile?.key ? <code>{parameters.profile.key}</code> : "None" },
    {
      term: "Rows that cannot load",
      value: parameters.policy === "atomic" ? "Load nothing unless every row loads" : "Load the rows that can load",
    },
    {
      term: "Records the file finds",
      value: parameters.onExisting === "overwrite" ? "Updated" : "Refused unless unchanged",
    },
    {
      term: "Records of another workspace",
      value: parameters.otherWorkspaceIds === "counterparts" ? "Loaded as this workspace's own" : "Refused",
    },
    { term: "Into", value: job.changeSetId ? "A change set" : "Live data" },
  ];
  return <DescriptionList className="compact" items={items} />;
}

/** What the file as a whole means here, before its rows are read one by one (0.9 J4a). */
export function ImportNotices({ job }: { job: Job }) {
  if (!job.notices?.length) return null;
  // Loaded as this workspace's own (0.9 J5) is information; refused is a reason rows cannot load.
  const loaded = job.notices.filter((notice) => notice.code === "RECORD_IDS_AS_COUNTERPARTS");
  const refused = job.notices.filter((notice) => notice.code !== "RECORD_IDS_AS_COUNTERPARTS");
  const lines = (notices: JobNotice[]) =>
    notices.map((notice) => <p key={notice.code + JSON.stringify(notice.details)}>{notice.message}</p>);
  return (
    <>
      {loaded.length > 0 && (
        <Notice tone="info" title="Another workspace's records">
          {lines(loaded)}
        </Notice>
      )}
      {refused.length > 0 && (
        <Notice tone="warning" title="Why rows cannot load here">
          {lines(refused)}
          <p>To load them as this workspace's own records, import the file again and choose so.</p>
        </Notice>
      )}
    </>
  );
}

export function ImportPreviewSection({ job }: { job: Job }) {
  const preview = job.preview;
  if (!preview) return null;
  const rows = preview.rows ?? { total: 0, previewed: 0, rejected: 0 };
  const atomic = parametersOf(job).policy === "atomic";
  const outcome =
    preview.result === "applied"
      ? "Loading would apply every row."
      : preview.result === "partial"
        ? `Loading would apply the rows that can load and refuse ${count(rows.rejected)} ${rows.rejected === 1 ? "row" : "rows"}.`
        : atomic
          ? "Loading would write nothing: with Load nothing unless every row loads, one refused row stops the whole file."
          : "Loading would write nothing: every row is refused.";
  return (
    <Section
      title={previewing(job) ? "The preview" : "What the preview said"}
      description={
        previewing(job)
          ? "Nothing was written. Data may change before you load the file; the load reads the file again."
          : "Before loading. The load read the file again, so the result and the rows above are its own."
      }
    >
      <Verdict
        result={preview.result}
        label={
          preview.result === "applied"
            ? "Every row loads"
            : preview.result === "partial"
              ? "Some rows refused"
              : "Nothing loads"
        }
      >
        {outcome}
      </Verdict>
      <DescriptionList
        className="compact"
        items={[
          { term: "Rows", value: `${count(rows.total)}, of which ${count(rows.rejected)} refused` },
          { term: "Created", value: count(preview.counts.created) },
          { term: "Updated", value: count(preview.counts.updated) },
          { term: "Unchanged", value: count(preview.counts.unchanged) },
          ...(preview.counts.deleted ? [{ term: "Deleted", value: count(preview.counts.deleted) }] : []),
          { term: "Refused items", value: count(preview.counts.rejected) },
        ]}
      />
      {preview.coverage === "sample" && (
        <Notice tone="info" title="A sample">
          The file is larger than one preview runs: the first {count(preview.items.previewed)} of{" "}
          {count(preview.items.total)} items ran, covering {count(rows.previewed)} of {count(rows.total)} rows fully.
          Every row was read and bound, so every refusal found while reading is listed.
        </Notice>
      )}
    </Section>
  );
}

/** After loading: what was applied, and how to act on refused rows without loading others twice. */
export function ImportResultSection({ job }: { job: Job }) {
  if (previewing(job) || job.state !== "completed") return null;
  const { applied, rejected, unprocessed, created, updated, unchanged } = job.counts;
  const definition = parametersOf(job).profile?.definition;
  return (
    <Section title="The result">
      <DescriptionList
        className="compact"
        items={[
          {
            term: "Applied items",
            value: `${count(applied)}: ${count(created)} created, ${count(updated)} updated, ${count(unchanged)} unchanged`,
          },
          { term: "Refused items", value: count(rejected) },
          { term: "Not loaded", value: count(unprocessed) },
        ]}
      />
      {rejected + unprocessed > 0 && (
        <Notice tone="info" title="Loading the refused rows">
          Correct the rows listed below in your file and import it again.{" "}
          {definition && keyless({ sources: definition.sources } as ImportProfile)
            ? "This profile has no key, so rows already loaded would be created again: send only the corrected rows."
            : "Rows already loaded are found again and come back unchanged, so nothing is loaded twice; the preview shows it."}
        </Notice>
      )}
    </Section>
  );
}

const BINDING: Record<BindingReportColumn["binding"], string> = {
  field: "Field",
  attributeTypeKey: "Attribute",
  key: "Record ID",
  parent: "Parent",
  relation: "Relationship",
  relationFlags: "Relationship flag",
  relatedRecord: "Related record",
};

function boundTo(model: EngineModel, column: BindingReportColumn): string {
  const target = column.target ?? "";
  switch (column.binding) {
    case "field":
    case "attributeTypeKey":
    case "key":
      return attributeName(model, target);
    case "parent":
    case "relatedRecord":
      return `${BINDING[column.binding]}: ${model.objectTypes.find((type) => type.key === target)?.name ?? target}`;
    default:
      return `${BINDING[column.binding]}: ${model.relationTypes.find((type) => type.key === target)?.name ?? target}`;
  }
}

/** A column whose every filled cell was refused, or a match column that found nothing. */
function suspicious(column: BindingReportColumn): boolean {
  const filled = column.cells - column.empty;
  if (filled === 0) return false;
  if (column.refused === filled) return true;
  return column.resolved !== undefined && column.resolved === 0;
}

/** A source as people read it: a CSV or JSON Lines file has one, named by its format. */
const sourceName = (sheet: string) =>
  sheet === "csv" ? "The CSV file" : sheet === "jsonl" ? "The JSON Lines file" : `Sheet ${sheet}`;

const dash = (value: number | undefined) => (value === undefined ? "—" : count(value));

export function BindingReportSection({ model, job }: { model: EngineModel; job: Job }) {
  const report = job.bindingReport;
  if (!report?.length) return null;
  return (
    <Section
      title="How the file was read"
      description="Per sheet and column: what each column is bound to and what became of its cells. A column marked Check is worth a look: every filled cell refused, or no value found a record."
    >
      {report.map((source, position) => (
        <div key={`${source.sheet}:${position}`} className="binding-source">
          <h3>
            {sourceName(source.sheet)}
            {source.objectTypeKey &&
              ` → ${model.objectTypes.find((type) => type.key === source.objectTypeKey)?.pluralName ?? source.objectTypeKey}`}
          </h3>
          <p className="admin-hint">
            {count(source.rows)} {source.rows === 1 ? "row" : "rows"}, {count(source.rejectedRows)} refused while
            reading.
          </p>
          <SettingsTable
            label={`Columns of ${sourceName(source.sheet).replace(/^The /, "the ")}`}
            columns={[
              "Column",
              "Bound to",
              "Cells",
              "Empty",
              "Read",
              "Value-mapped",
              "Refused",
              "Found",
              "Not found",
              "Ambiguous",
            ]}
          >
            {source.columns.map((column) => (
              <tr key={`${column.column}:${column.binding}:${column.target}`}>
                <th scope="row">
                  <span className="binding-column">
                    {column.column}
                    {suspicious(column) && <StatusPill tone="warning">Check</StatusPill>}
                  </span>
                </th>
                <td data-label="Bound to">{boundTo(model, column)}</td>
                <td data-label="Cells">{count(column.cells)}</td>
                <td data-label="Empty">{count(column.empty)}</td>
                <td data-label="Read">{dash(column.converted)}</td>
                <td data-label="Value-mapped">{dash(column.valueMapped)}</td>
                <td data-label="Refused">{count(column.refused)}</td>
                <td data-label="Found">{dash(column.resolved)}</td>
                <td data-label="Not found">{dash(column.notFound)}</td>
                <td data-label="Ambiguous">{dash(column.ambiguous)}</td>
              </tr>
            ))}
          </SettingsTable>
        </div>
      ))}
    </Section>
  );
}

type RowFilter = JobRow["status"] | "all";

function rowName(row: JobRow): string {
  if (!row.sheet || row.sheet === "csv") return `Row ${row.row}`;
  if (row.sheet === "jsonl") return `Line ${row.row}`;
  return `${row.sheet}, row ${row.row}`;
}

/** Each failing cell of a refused item, else its error: "Order: … is not a whole number". */
function problems(outcome: JobItemOutcome): string[] {
  const error = outcome.error;
  if (!error) return [];
  const details = (error.details ?? {}) as { cells?: { column: string; message: string }[]; column?: string };
  if (Array.isArray(details.cells) && details.cells.length)
    return details.cells.map((cell) => `${cell.column}: ${cell.message}`);
  return [details.column ? `${details.column}: ${error.message}` : error.message];
}

function actionText(row: JobRow, preview: boolean): string {
  const parts = (["created", "updated", "unchanged", "deleted"] as const)
    .filter((action) => row.actions[action])
    .map((action) => `${count(row.actions[action])} ${action}`);
  return parts.length ? `${preview ? "Would be " : ""}${parts.join(", ")}` : "";
}

export function ImportRowsSection({ job }: { job: Job }) {
  const preview = previewing(job);
  const refused = preview ? (job.preview?.rows?.rejected ?? 0) : job.counts.rejected + job.counts.unprocessed;
  const [filter, setFilter] = useState<RowFilter>(refused > 0 ? "rejected" : "all");
  // The rows are read again when the preview's outcomes give way to the execution's.
  const list = useCursorWindow<JobRow>(
    (selector) =>
      api.jobRows(job.id, { ...selector, pageSize: ROWS_PAGE, ...(filter === "all" ? {} : { status: filter }) }),
    [job.id, filter, job.state, job.confirmedAt],
  );
  const STATUS: Record<JobRow["status"], { label: string; tone: "success" | "error" | "neutral" }> = {
    applied: { label: preview ? "Loads" : "Loaded", tone: "success" },
    rejected: { label: "Refused", tone: "error" },
    unprocessed: { label: "Not loaded", tone: "neutral" },
  };
  const columns: DataColumn<JobRow>[] = [
    { key: "row", label: "Row", cell: (row) => rowName(row) },
    {
      key: "status",
      label: "Outcome",
      cell: (row) => <StatusPill tone={STATUS[row.status].tone}>{STATUS[row.status].label}</StatusPill>,
    },
    {
      key: "detail",
      label: "Why, or what it does",
      cell: (row) => {
        const lines = row.outcomes.flatMap(problems);
        return lines.length ? (
          <ul className="row-problems">
            {lines.map((line, position) => (
              <li key={position}>{line}</li>
            ))}
          </ul>
        ) : (
          actionText(row, preview)
        );
      },
    },
  ];
  return (
    <Section
      title={preview ? "Rows in the preview" : "Rows"}
      description="Each row of the file with what loading it does or why it cannot load, in sheet and row order."
    >
      <div className="rows-filter">
        <Choice
          name="import-rows"
          value={filter}
          options={[
            ["rejected", "Refused"],
            ["unprocessed", "Not loaded"],
            ["all", "All rows"],
          ]}
          onChange={setFilter}
        />
      </div>
      <DataTable<JobRow>
        columns={columns}
        list={list}
        rowKey={(row) => row.ref}
        rowAttributes={() => ({ tabIndex: -1 })}
        label="Rows of the file"
        noun={["row", "rows"]}
        pageSize={ROWS_PAGE}
        emptyMessage={filter === "all" ? "No rows were read." : "No rows here."}
      />
    </Section>
  );
}
