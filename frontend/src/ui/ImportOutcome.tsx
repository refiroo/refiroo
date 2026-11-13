/**
 * What an import's job page shows beside its state (0.9 J4, J27.13): the file and profile, the
 * preview (counts, the result under the chosen policy, whether it covered every item), after
 * loading the result and how to act on refused rows (D94), the binding report per source and
 * column (D86), and the file's rows with their outcomes, paged (D84). Names come from the model;
 * nothing names a type.
 */

import { useState, type DependencyList } from "react";
import { api, type PageSelector } from "@/api/client";
import { errorMessage } from "@/api/errors";
import { attributeName } from "@/model/fields";
import { useCursorWindow } from "@/lib/hooks/useCursorWindow";
import type {
  BindingReportColumn,
  EngineModel,
  ImportProfile,
  ImportProfileSource,
  Job,
  JobItemOutcome,
  JobNotice,
  JobRow,
  JobRowPage,
  RouteState,
} from "@/types";
import { Choice } from "@/ui/Choice";
import { DataTable, type DataColumn } from "@/ui/DataTable";
import { DescriptionList, type DescriptionItem } from "@/ui/DescriptionList";
import { Notice } from "@/ui/Notice";
import { Section } from "@/ui/Section";
import { SettingsTable } from "@/ui/SettingsTable";
import { StatusPill } from "@/ui/StatusPill";
import { count } from "@/ui/limits";
import { keyless } from "@/model/importRequest";
import { Verdict } from "./Verdict";
import { fileSize } from "@/ui/jobText";

const ROWS_PAGE = 50;

interface ImportParameters {
  policy?: "atomic" | "independent";
  onExisting?: "reject" | "overwrite";
  otherWorkspaceIds?: "refuse" | "counterparts";
  file?: { name: string; format: string; bytes: number };
  profile?: {
    key: string | null;
    version: number | null;
    definition?: Pick<ImportProfile, "sources">;
    /** What a workbook for people says it is, when its own profile read it (0.9 J6, D185). */
    embedded?: { collection?: string; exportedAt?: string };
  } | null;
}

const parametersOf = (job: Job) => job.parameters as ImportParameters;

/** "Import of codes.csv", or "Import" before the file is known. */
export function importTitle(job: Job): string {
  const name = parametersOf(job).file?.name;
  return name ? `Import of ${name}` : "Import";
}

/** The profile that read the file: a stored one's key, the one a workbook for people carries ("Read as
 * exported from Values on 10 Oct 2026"), or none. */
export function profileText(profile: ImportParameters["profile"]) {
  if (profile?.key) return <code>{profile.key}</code>;
  const embedded = profile?.embedded;
  if (!embedded) return profile?.definition ? "Given with the request" : "None";
  const day = embedded.exportedAt
    ? new Date(embedded.exportedAt).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" })
    : undefined;
  return `Read as exported from ${embedded.collection ?? "a collection"}${day ? ` on ${day}` : ""}`;
}

/** The preview's outcomes are the job's until it is confirmed; then the execution's replace them. */
const previewing = (job: Job) => !job.confirmedAt;

export function ImportFacts({ job }: { job: Job }) {
  const parameters = parametersOf(job);
  const items: DescriptionItem[] = [
    ...(parameters.file
      ? [{ term: "File", value: `${parameters.file.name} (${fileSize(parameters.file.bytes)})` }]
      : []),
    { term: "Profile", value: profileText(parameters.profile) },
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

/**
 * How the preview reads each matrix and relationship column (0.17 PP-D26): the field its cells are
 * matched by, how many values found a record, where a new record goes, and a choice of another
 * field, which runs the preview again. Nothing is written by either preview.
 */
export function ImportReadingSection({ job, onNavigate }: { job: Job; onNavigate?: (route: RouteState) => void }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);
  const columns = (job.bindingReport ?? []).flatMap((source, position) =>
    source.columns.filter((column) => column.reading).map((column) => ({ source: position, column })),
  );
  if (!columns.length) return null;
  const profile = parametersOf(job).profile;

  async function change(source: number, column: string, field: string) {
    setBusy(true);
    setError("");
    try {
      const next = await api.rereadImport(job.id, [{ source, column, field }]);
      onNavigate?.({ kind: "settings", page: "jobs", jobId: next.id });
    } catch (cause) {
      setError(errorMessage(cause));
      setBusy(false);
    }
  }

  async function save() {
    if (!profile?.key || !profile.definition) return;
    setBusy(true);
    setError("");
    try {
      const stored = await api.importProfile(profile.key, job.workspaceKey);
      await api.updateImportProfile(
        stored,
        profile.definition.sources as unknown as ImportProfileSource[],
        job.workspaceKey,
      );
      setSaved(true);
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Section
      title="How the file is read"
      description="Per column: the field its cells are matched by, the rows of a value sheet, and where a new record goes. Choosing another field reads the file again; nothing is written until you load it."
    >
      {error && (
        <Notice tone="error" title="The file could not be read again">
          {error}
        </Notice>
      )}
      <SettingsTable
        label="How each column is read"
        columns={["Column", "Matched by", "Values matched", "New records go into"]}
      >
        {columns.map(({ source, column }) => {
          const reading = column.reading!;
          const current = reading.options.find((option) => option.field === reading.field);
          const where = reading.newRecords;
          return (
            <tr key={`${source}:${column.column}`}>
              <th scope="row">{column.column}</th>
              <td data-label="Matched by">
                {reading.valueSheet ? (
                  "Value sheet: a row with an ID updates its record, one without is new"
                ) : reading.options.length > 1 ? (
                  <select
                    aria-label={`Field ${column.column} is matched by`}
                    value={reading.field ?? ""}
                    disabled={busy}
                    onChange={(event) => void change(source, column.column, event.target.value)}
                  >
                    {reading.field === "@label" && <option value="@label">{reading.label}</option>}
                    {reading.options.map((option) => (
                      <option key={option.field} value={option.field}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                ) : (
                  (reading.label ?? "")
                )}
                {reading.guessed && <StatusPill tone="neutral">Guessed</StatusPill>}
                {reading.note && <p className="admin-hint">{reading.note}</p>}
              </td>
              <td data-label="Values matched">
                {reading.valueSheet
                  ? `${count(reading.updatedRows ?? 0)} rows update a record, ${count(reading.newRows ?? 0)} are new`
                  : current?.cells
                    ? `${count(current.matched ?? 0)} of ${count(current.cells)}` +
                      (reading.fromValueSheet ? `, ${count(reading.fromValueSheet)} from the value sheet` : "") +
                      (reading.createdValues ? `, ${count(reading.createdValues)} new` : "")
                    : "—"}
              </td>
              <td data-label="New records go into">
                {!where
                  ? "—"
                  : where.name
                    ? where.willBeCreated && where.under
                      ? `will create ${(where.typeName ?? "group").toLowerCase()} “${where.name}” under ${where.under}`
                      : `${where.name}${where.willBeCreated ? " (will be created)" : ""}`
                    : (where.message ??
                      (where.reason === "several"
                        ? "Several places meet the rules: a new record is refused"
                        : "No place the rules allow: a new record is refused"))}
              </td>
            </tr>
          );
        })}
      </SettingsTable>
      {profile?.key && (
        <p>
          <button type="button" className="secondary" disabled={busy || saved} onClick={() => void save()}>
            {saved ? "Saved in the profile" : "Save these fields in the profile"}
          </button>
        </p>
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
  return (
    <Section
      title={preview ? "Rows in the preview" : "Rows"}
      description="Each row of the file with what loading it does or why it cannot load, in sheet and row order."
    >
      <JobRowsTable
        name="import-rows"
        preview={preview}
        initialFilter={refused > 0 ? "rejected" : "all"}
        // The rows are read again when the preview's outcomes give way to the execution's.
        deps={[job.id, job.state, job.confirmedAt]}
        rows={(query) => api.jobRows(job.id, query)}
      />
    </Section>
  );
}

/**
 * A file's rows with their outcomes, filtered by status and paged (D84): an import's, or a dry
 * run's rows behind one of its figures (0.10 A5b). `preview` words them as what loading would do.
 */
export function JobRowsTable({
  name,
  rows,
  deps,
  preview,
  initialFilter,
}: {
  name: string;
  rows: (query: PageSelector & { status?: JobRow["status"]; pageSize: number }) => Promise<JobRowPage>;
  deps: DependencyList;
  preview: boolean;
  initialFilter: RowFilter;
}) {
  const [filter, setFilter] = useState<RowFilter>(initialFilter);
  const list = useCursorWindow<JobRow>(
    (selector) => rows({ ...selector, pageSize: ROWS_PAGE, ...(filter === "all" ? {} : { status: filter }) }),
    [...deps, filter],
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
    <>
      <div className="rows-filter">
        <Choice
          name={name}
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
    </>
  );
}
