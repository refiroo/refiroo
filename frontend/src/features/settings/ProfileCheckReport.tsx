/**
 * What a profile's check found in its next file (0.10 A5c, D83), in the approved board's four parts:
 * Columns (new, renamed, missing, each with what to do), Values (new values of match columns, name
 * drift), Records (what the load adds, changes, keeps and what the file no longer names, with the
 * profile's choice for those) and the profile against the active release with the dry run's
 * refusals. Each list opens its rows; nothing here writes data, and every change is to the profile.
 */

import { useEffect, useState } from "react";
import { api } from "@/api/client";
import type { CheckDrift, CheckMissingRecord, CheckNewValue, CheckSource, DryRunSource, ProfileCheck } from "@/types";
import { useCursorWindow } from "@/lib/hooks/useCursorWindow";
import { DataTable, type DataColumn } from "@/ui/DataTable";
import { Modal } from "@/ui/Modal";
import { Section } from "@/ui/Section";
import { StatusPill } from "@/ui/StatusPill";
import { JobRowsTable } from "@/features/jobs/ImportOutcome";
import { count } from "./limits";

export type CheckList = "new-values" | "drift" | "missing-records";

/** A list or the rows behind a figure, opened in a dialog. */
export type CheckRows =
  | { kind: "list"; list: CheckList; source: number; title: string }
  | { kind: "rows"; source: number; code?: string; title: string };

/** How many things the check asks to look at before loading. */
export function differences(check: ProfileCheck): number {
  let found = check.problems.length;
  for (const source of check.sources) {
    const columns = source.columns;
    found += (columns?.new.length ?? 0) + (columns?.renamed.length ?? 0) + (columns?.missing.length ?? 0);
    found += (source.newValues ? 1 : 0) + (source.drift ? 1 : 0) + (source.missingRecords ? 1 : 0);
    if (!source.sheetFound) found += 1;
  }
  return found;
}

/** Whether loading the file through the profile as it stands would read every column it names. */
export function loadable(check: ProfileCheck): boolean {
  return (
    check.state === "completed" &&
    check.valid === true &&
    check.sources.every(
      (source) => source.sheetFound && !source.columns?.missing.length && !source.columns?.renamed.length,
    )
  );
}

function figures(check: ProfileCheck, source: CheckSource): DryRunSource | undefined {
  return check.dryRun?.sources.find((item) => item.source === source.source);
}

export function ProfileCheckReport({
  check,
  typeName,
  busy,
  onRename,
  onIgnore,
  onMissing,
  onOpen,
}: {
  check: ProfileCheck;
  typeName: (key: string) => string;
  /** A change to the profile is being saved. */
  busy: boolean;
  onRename: (source: CheckSource, from: string, to: string) => void;
  onIgnore: (source: CheckSource, column: string) => void;
  onMissing: (source: CheckSource, missing: "report" | "delete") => void;
  onOpen: (rows: CheckRows) => void;
}) {
  const several = check.sources.length > 1;
  const named = (source: CheckSource) =>
    several ? `${typeName(source.objectTypeKey)} from ${source.sheet ?? "the file"} · ` : "";
  const refused = (check.dryRun?.sources ?? []).reduce(
    (total, source) => total + source.rejections.reduce((sum, item) => sum + item.rows, 0),
    0,
  );
  return (
    <div className="check-grid">
      <Section title="Columns">
        <ul className="check-lines">
          {check.sources.map((source) =>
            !source.sheetFound ? (
              <li key={`sheet-${source.profileSource}`}>
                <span>
                  <StatusPill tone="error">Missing</StatusPill> {named(source)}sheet <strong>{source.sheet}</strong> is
                  not in the file; its rows are not read
                </span>
              </li>
            ) : (
              <SourceColumns
                key={source.profileSource}
                source={source}
                prefix={named(source)}
                busy={busy}
                onRename={onRename}
                onIgnore={onIgnore}
              />
            ),
          )}
        </ul>
      </Section>
      <Section title="Values">
        <ul className="check-lines">
          {check.sources.map((source) => (
            <SourceValues
              key={source.profileSource}
              source={source}
              prefix={named(source)}
              profileKey={check.profileKey}
              onOpen={onOpen}
            />
          ))}
        </ul>
      </Section>
      <Section title="Records">
        {check.sources.map((source) => {
          const found = figures(check, source);
          return (
            <ul className="check-lines" key={source.profileSource} aria-label={several ? named(source) : undefined}>
              {several && <li className="check-source">{named(source).replace(/ · $/, "")}</li>}
              {found ? (
                <>
                  <li>
                    <span>Added</span>
                    <strong>{count(found.records.created)}</strong>
                  </li>
                  <li>
                    <span>Changed</span>
                    <strong>{count(found.records.updated)}</strong>
                  </li>
                  <li>
                    <span>Unchanged</span>
                    <strong>{count(found.records.unchanged)}</strong>
                  </li>
                </>
              ) : (
                <li>
                  <span className="muted">
                    Not read: {source.source === null ? "see the profile's problems" : "no dry run"}
                  </span>
                </li>
              )}
              <li>
                <span>Missing from the file</span>
                <span className="check-figure">
                  {source.missingRecords > 0 && (
                    <button
                      type="button"
                      className="secondary"
                      onClick={() =>
                        onOpen({
                          kind: "list",
                          list: "missing-records",
                          source: source.source ?? 0,
                          title: `Records missing from the file · ${typeName(source.objectTypeKey)}`,
                        })
                      }
                    >
                      Show rows
                    </button>
                  )}
                  <strong>{count(source.missingRecords)}</strong>
                </span>
              </li>
              <li className="check-choice">
                <label>
                  <span>When loading</span>
                  <select
                    className="field-input"
                    value={source.missing}
                    disabled={busy}
                    onChange={(event) => onMissing(source, event.target.value as "report" | "delete")}
                  >
                    <option value="report">Keep the missing records</option>
                    <option value="delete">Delete them in the change set</option>
                  </select>
                </label>
              </li>
            </ul>
          );
        })}
      </Section>
      <Section title="Profile against the active release">
        <ul className="check-lines">
          <li>
            <span>{check.valid ? "Every binding resolves" : "Bindings that no longer resolve"}</span>
            <StatusPill tone={check.valid ? "success" : "error"}>{check.valid ? "Valid" : "Needs a fix"}</StatusPill>
          </li>
          {check.problems.map((problem) => (
            <li key={`${problem.path}-${problem.code}`} className="check-problem">
              <span>
                <code>{problem.path}</code> {problem.message}
              </span>
              <code>{problem.code}</code>
            </li>
          ))}
          {check.dryRun && (
            <li>
              <span>Dry run · all {count(check.dryRun.rows.total)} rows</span>
              <span className="check-figure">
                {refused > 0 && (
                  <button
                    type="button"
                    className="secondary"
                    onClick={() => onOpen({ kind: "rows", source: 0, title: "Rows the load would refuse" })}
                  >
                    Show rows
                  </button>
                )}
                <span>{count(refused)} refused</span>
              </span>
            </li>
          )}
        </ul>
        {!check.valid && (
          <p className="section-description">
            Loading is refused until the profile holds against the active release. Fix it in the model editor, or
            through <code>PUT /api/v1/import-profiles/{check.profileKey}</code>.
          </p>
        )}
      </Section>
    </div>
  );
}

function SourceColumns({
  source,
  prefix,
  busy,
  onRename,
  onIgnore,
}: {
  source: CheckSource;
  prefix: string;
  busy: boolean;
  onRename: (source: CheckSource, from: string, to: string) => void;
  onIgnore: (source: CheckSource, column: string) => void;
}) {
  const columns = source.columns;
  if (!columns) return null;
  const nothing = !columns.new.length && !columns.renamed.length && !columns.missing.length;
  return (
    <>
      {columns.new.map((item) => (
        <li key={`new-${item.column}`}>
          <span>
            <StatusPill tone="neutral">New</StatusPill> {prefix}
            <strong>{item.column}</strong> · column {item.letter}
          </span>
          <button type="button" className="secondary" disabled={busy} onClick={() => onIgnore(source, item.column)}>
            Ignore
          </button>
        </li>
      ))}
      {columns.renamed.map((item) => (
        <li key={`renamed-${item.from}`}>
          <span>
            <StatusPill tone="warning">Renamed</StatusPill> {prefix}
            <strong>{item.from}</strong> → <strong>{item.to}</strong> · same position, {Math.round(item.shared * 100)}%
            of values shared
          </span>
          <button
            type="button"
            className="secondary"
            disabled={busy}
            onClick={() => onRename(source, item.from, item.to)}
          >
            Accept
          </button>
        </li>
      ))}
      {columns.missing.map((item) => (
        <li key={`missing-${item.column}`}>
          <span>
            <StatusPill tone="error">Missing</StatusPill> {prefix}
            <strong>{item.column}</strong> · the profile reads it; a load is refused until the file has it again
          </span>
        </li>
      ))}
      {nothing && (
        <li>
          <span className="muted">{prefix}The file has the columns the profile reads, and no new ones</span>
        </li>
      )}
    </>
  );
}

function SourceValues({
  source,
  prefix,
  profileKey,
  onOpen,
}: {
  source: CheckSource;
  prefix: string;
  profileKey: string;
  onOpen: (rows: CheckRows) => void;
}) {
  const [shown, setShown] = useState<CheckNewValue[]>([]);
  const at = source.source;
  useEffect(() => {
    let cancelled = false;
    if (at === null || !source.newValues) return;
    api
      .profileCheckList<CheckNewValue>(profileKey, "new-values", { source: at, pageSize: 5 })
      .then((page) => {
        if (!cancelled) setShown(page.items);
      })
      .catch(() => {
        // The count stands on its own; the list opens in full from Rows.
      });
    return () => {
      cancelled = true;
    };
  }, [profileKey, at, source.newValues]);
  if (at === null) return null;
  const visible = source.newValues ? shown : [];
  return (
    <>
      {visible.map((item) => (
        <li key={`${item.column}-${String(item.value)}`}>
          <span>
            <StatusPill tone="neutral">New</StatusPill> {prefix}
            {item.column} <strong>{String(item.value)}</strong> · {count(item.cells)}{" "}
            {item.cells === 1 ? "row" : "rows"}
          </span>
          <span className="muted">{item.created ? "created by the load" : "refused: no such record"}</span>
        </li>
      ))}
      {source.newValues > visible.length && (
        <li>
          <span>
            {prefix}
            {count(source.newValues)} new values in all
          </span>
          <button
            type="button"
            className="secondary"
            onClick={() => onOpen({ kind: "list", list: "new-values", source: at, title: "New values" })}
          >
            Show rows
          </button>
        </li>
      )}
      <li>
        <span>
          {source.drift > 0 && <StatusPill tone="warning">Drift</StatusPill>} {prefix}
          {source.drift
            ? `${count(source.drift)} ${source.drift === 1 ? "record has" : "records have"} another name than the live record`
            : "Every record found keeps its name"}
        </span>
        {source.drift > 0 && (
          <button
            type="button"
            className="secondary"
            onClick={() => onOpen({ kind: "list", list: "drift", source: at, title: "Names that drifted" })}
          >
            Show rows
          </button>
        )}
      </li>
    </>
  );
}

const LIST_COLUMNS = {
  "new-values": [
    { key: "column", label: "Column", cell: (row: CheckNewValue) => row.column },
    { key: "value", label: "Value", cell: (row: CheckNewValue) => String(row.value) },
    { key: "cells", label: "Rows", cell: (row: CheckNewValue) => count(row.cells) },
    {
      key: "created",
      label: "When loading",
      cell: (row: CheckNewValue) => (row.created ? "Created" : "Refused: no such record"),
    },
  ] satisfies DataColumn<CheckNewValue>[],
  drift: [
    { key: "row", label: "Row", cell: (row: CheckDrift) => row.row },
    { key: "key", label: "Key", cell: (row: CheckDrift) => String(row.key) },
    { key: "name", label: "In the file", cell: (row: CheckDrift) => row.name },
    { key: "recordName", label: "The record's name", cell: (row: CheckDrift) => row.recordName ?? "" },
  ] satisfies DataColumn<CheckDrift>[],
  "missing-records": [
    { key: "name", label: "Record", cell: (row: CheckMissingRecord) => row.name },
    { key: "key", label: "Key", cell: (row: CheckMissingRecord) => String(row.key) },
  ] satisfies DataColumn<CheckMissingRecord>[],
};

/** A list of the check, or the rows behind its dry run's refusals. */
export function CheckRowsDialog({
  profileKey,
  rows,
  onClose,
}: {
  profileKey: string;
  rows: CheckRows;
  onClose: () => void;
}) {
  return (
    <Modal
      title={rows.title}
      eyebrow="Check of the next version"
      description="Nothing was written: this is what loading would find."
      size="wide"
      onClose={onClose}
    >
      <div className="dialog-body">
        {rows.kind === "rows" ? (
          <JobRowsTable
            name="check-rows"
            preview
            initialFilter="rejected"
            deps={[profileKey, rows.source, rows.code]}
            rows={(query) => api.profileCheckRows(profileKey, { ...query, code: rows.code })}
          />
        ) : (
          <CheckListTable profileKey={profileKey} list={rows.list} source={rows.source} />
        )}
      </div>
    </Modal>
  );
}

function CheckListTable({ profileKey, list, source }: { profileKey: string; list: CheckList; source: number }) {
  const window = useCursorWindow<CheckNewValue | CheckDrift | CheckMissingRecord>(
    (selector) => api.profileCheckList(profileKey, list, { ...selector, source, pageSize: 100 }),
    [profileKey, list, source],
  );
  return (
    <DataTable
      columns={LIST_COLUMNS[list] as DataColumn<CheckNewValue | CheckDrift | CheckMissingRecord>[]}
      list={window}
      rowKey={(row) =>
        "recordId" in row ? `${row.recordId}-${"row" in row ? row.row : ""}` : `${row.column}-${String(row.value)}`
      }
      label="Found in the file"
      noun={["entry", "entries"]}
      pageSize={100}
      emptyMessage="Nothing here."
    />
  );
}
