/**
 * A column of the draft's source file in the editor's centre (0.10 A5b, D84): what it feeds, how it
 * is read and matched, its split, whether values that do not exist are created (D77), its value
 * map, whether it is its source's key, its statistics (A3) and the dry run's refused rows of its
 * source. Each change is one step; Map to… and Ignore act on the whole column.
 */

import { useEffect, type ReactNode } from "react";
import type { DraftOperation, DryRun, ModelDraftOutline, SourceColumn } from "@/types";
import type { DraftSource } from "@/features/model-editor/useDraftSource";
import { StatusPill } from "@/ui/StatusPill";
import { ProposedPill } from "@/ui/ProposedBecause";
import { ColumnReadings, ReadingMarks } from "@/features/model-editor/ReadingEntries";
import { sourceOfColumn } from "@/features/model-editor/readings";
import { typeName, attributeTypeOf } from "@/model/outline";
import {
  columnState,
  delimiterLabel,
  issuesByColumn,
  matchWords,
  readingWords,
  relationPart,
  STATUS_LABELS,
  feedWords,
  type ColumnStatus,
  type ColumnUse,
} from "@/features/model-editor/mapping";

const TONES: Record<ColumnStatus, "success" | "neutral" | "warning" | "proposed"> = {
  key: "success",
  mapped: "success",
  proposed: "proposed",
  unmapped: "neutral",
  ignored: "neutral",
  describes: "neutral",
  issue: "warning",
};

const SPLITS = [";", ",", "|", "/", "\n"];

/** The dry run's figures of the source a use belongs to, by its place among the loaded sources. */
export function dryRunSourceOf(source: DraftSource, sourceId: string, dryRun: DryRun | undefined) {
  const loaded = (source.profile?.profile?.sources ?? []).filter((item) => item.columns.length > 0);
  const position = loaded.findIndex((item) => item.id === sourceId);
  return dryRun?.summary?.sources.find((item) => item.profileSource === position);
}

export function ColumnPanel({
  sheet,
  header,
  source,
  outline,
  busy,
  run,
  onMap,
  onValueMap,
  onRows,
  proposed,
}: {
  /** Why the column is mapped as it is, while it is still as proposed (0.10 A6b, D94). */
  proposed?: ReactNode;
  sheet: string;
  header: string;
  source: DraftSource;
  outline: ModelDraftOutline;
  busy: boolean;
  run: (operations: DraftOperation[]) => void;
  onMap: () => void;
  onValueMap: (use: ColumnUse) => void;
  onRows: (rows: { source: number; status: "rejected"; code?: string; title: string }) => void;
}) {
  const { loadColumns } = source;
  // Opened from the address or the phone's tab, the sheet's columns may not be read yet.
  useEffect(() => {
    if (source.sheets.length) loadColumns(sheet);
  }, [loadColumns, sheet, source.sheets.length]);
  const column: SourceColumn | undefined = source.columns(sheet)?.find((item) => item.header === header);
  const state = columnState(source.profile, issuesByColumn(source.profile), sheet, header);
  const uses = state.uses.filter((use) => !use.binding.ignore);
  const first = uses[0];
  const relation = first ? relationPart(first.binding) : undefined;
  const byName = relation?.matchBy?.field === "name" && !first?.binding.relationFlags;
  const loaded = first ? dryRunSourceOf(source, first.source.id, source.dryRun) : undefined;
  const refused = loaded?.rejections.reduce((total, item) => total + item.rows, 0) ?? 0;
  const keyed =
    first?.binding.attributeTypeKey !== undefined &&
    first.source.key?.attributeTypeKey === first.binding.attributeTypeKey;
  const unique = first?.binding.attributeTypeKey
    ? Boolean(
        outline.objectTypes
          .find((type) => type.key === first.source.objectTypeKey)
          ?.attributes.find((item) => item.attributeType === first.binding.attributeTypeKey)?.unique,
      )
    : false;
  const at = first ? { source: first.source.id, column: header } : undefined;
  const document = source.profile?.profile;
  const readingOwner = sourceOfColumn(document, sheet, header);
  const sheetColumns = source.columns(sheet);

  return (
    <div className="column-panel">
      <header className="element-header">
        <div className="element-title">
          <p className="eyebrow">
            Column {column?.letter ?? ""} of {sheet}
          </p>
          <h2 id="element-title">{header}</h2>
          {proposed && state.status !== "issue" ? (
            <ProposedPill />
          ) : (
            <StatusPill tone={TONES[state.status]}>{STATUS_LABELS[state.status]}</StatusPill>
          )}
        </div>
        <div className="element-actions">
          <button type="button" className="primary" onClick={onMap} disabled={busy}>
            Map to…
          </button>
          {state.status !== "ignored" && (
            <button
              type="button"
              className="secondary"
              disabled={busy}
              onClick={() => {
                const sourceId =
                  state.uses[0]?.source.id ?? source.profile?.profile?.sources.find((s) => s.sheet === sheet)?.id;
                if (sourceId) run([{ kind: "ignoreColumn", source: sourceId, column: header }]);
                else onMap();
              }}
            >
              Ignore
            </button>
          )}
        </div>
      </header>

      {proposed}

      {state.issues.length > 0 && (
        <ul className="column-issues">
          {state.issues.map((item, index) => (
            <li key={index}>
              <StatusPill tone="warning">Warning</StatusPill> {item.message}
            </li>
          ))}
        </ul>
      )}

      <dl className="column-facts">
        <div>
          <dt>Feeds</dt>
          <dd>
            {uses.length ? (
              <ul className="plain-list">
                {uses.map((use) => (
                  <li key={use.source.id}>{feedWords(outline, use, header)}</li>
                ))}
              </ul>
            ) : state.status === "ignored" ? (
              "Ignored: kept out of the load"
            ) : (
              "Not mapped"
            )}
          </dd>
        </div>
        {first && (
          <>
            <div>
              <dt>Read as</dt>
              <dd>{readingWords(first.binding)}</dd>
            </div>
            <div>
              <dt>Matched by</dt>
              <dd>{matchWords(outline, relation)}</dd>
            </div>
          </>
        )}
        {first?.binding.relation && at && (
          <div>
            <dt>
              <label htmlFor="column-split">Split on</label>
            </dt>
            <dd>
              <select
                id="column-split"
                value={first.binding.relation.split ?? ""}
                disabled={busy}
                onChange={(event) => run([{ kind: "splitColumn", ...at, delimiter: event.target.value || null }])}
              >
                <option value="">Do not split</option>
                {SPLITS.map((item) => (
                  <option key={item} value={item}>
                    {delimiterLabel(item)}
                  </option>
                ))}
              </select>
            </dd>
          </div>
        )}
        {byName && at && (
          <div>
            <dt>Not found</dt>
            <dd>
              <label className="checkbox">
                <input
                  type="checkbox"
                  checked={relation?.missing === "create"}
                  disabled={busy}
                  onChange={(event) => run([{ kind: "addValuesToList", ...at, create: event.target.checked }])}
                />
                Create the {typeName(outline, relation?.objectTypeKey ?? "")} records a cell names that do not exist
              </label>
            </dd>
          </div>
        )}
        {readingOwner && (
          <div>
            <dt>Readings</dt>
            <dd className="column-readings">
              <ReadingMarks profile={document} sheet={sheet} header={header} />
              <ColumnReadings
                owner={readingOwner}
                header={header}
                headers={(sheetColumns ?? []).flatMap((item) => (item.header ? [item.header] : []))}
                profile={document}
                outline={outline}
                columns={sheetColumns}
                sheet={sheet}
                busy={busy}
                run={run}
              />
            </dd>
          </div>
        )}
        {first && !first.binding.relationFlags && (
          <div>
            <dt>Value map</dt>
            <dd className="column-value-map">
              {first.binding.valueMap ? (
                <span>
                  {Object.entries(source.profile?.profile?.valueMaps[first.binding.valueMap] ?? {})
                    .map(([text, value]) => `${text} → ${value === null ? "empty" : String(value)}`)
                    .join(" · ") || "No values"}
                </span>
              ) : (
                <span className="muted">None</span>
              )}
              <button type="button" className="secondary" disabled={busy} onClick={() => onValueMap(first)}>
                {first.binding.valueMap ? "Edit value map…" : "Add a value map…"}
              </button>
            </dd>
          </div>
        )}
        {first?.binding.attributeTypeKey && (
          <div>
            <dt>Key</dt>
            <dd>
              {keyed ? (
                `The key of the rows: a row updates the ${typeName(outline, first.source.objectTypeKey)} with its value`
              ) : unique ? (
                <button
                  type="button"
                  className="secondary"
                  disabled={busy}
                  onClick={() =>
                    run([
                      {
                        kind: "setSource",
                        source: first.source.id,
                        key: { attributeTypeKey: first.binding.attributeTypeKey },
                      },
                    ])
                  }
                >
                  Use as the key of the rows
                </button>
              ) : (
                <span className="muted">
                  Not the key: {attributeTypeOf(outline, first.binding.attributeTypeKey)?.name} is not unique
                </span>
              )}
            </dd>
          </div>
        )}
        {loaded && (
          <div>
            <dt>Dry run</dt>
            <dd>
              {refused ? (
                <button
                  type="button"
                  className="link-button"
                  onClick={() =>
                    onRows({
                      source: loaded.source,
                      status: "rejected",
                      title: `Rows of ${sheet} refused for ${typeName(outline, loaded.objectTypeKey)}`,
                    })
                  }
                >
                  {refused} rows of the source refused
                </button>
              ) : (
                `No row of the source refused (${loaded.rows} rows)`
              )}
            </dd>
          </div>
        )}
      </dl>

      {column && (
        <section className="column-statistics" aria-labelledby="column-statistics">
          <h3 id="column-statistics">Statistics</h3>
          <dl className="column-facts">
            <div>
              <dt>Filled</dt>
              <dd>
                {column.filled} of {column.rows} rows · {column.distinct} distinct
                {column.candidateKey ? " · no value twice: a candidate key" : ""}
              </dd>
            </div>
            <div>
              <dt>Values read as</dt>
              <dd>
                {Object.entries(column.valueTypes)
                  .filter(([, cells]) => cells > 0)
                  .map(([type, cells]) => `${type} ${cells}`)
                  .join(" · ") || "—"}
              </dd>
            </div>
            {(column.values ?? []).length > 0 && (
              <div>
                <dt>Most frequent values</dt>
                <dd>
                  <ul className="plain-list column-values">
                    {(column.values ?? []).map((item) => (
                      <li key={item.value}>
                        <span>{item.value}</span> <span className="muted">{item.count} rows</span>
                      </li>
                    ))}
                  </ul>
                </dd>
              </div>
            )}
            {column.placeholders.length > 0 && (
              <div>
                <dt>Placeholders</dt>
                <dd>{column.placeholders.map((item) => `${item.value} ×${item.count}`).join(" · ")}</dd>
              </div>
            )}
            {column.delimiters.length > 0 && (
              <div>
                <dt>Delimiters</dt>
                <dd>
                  {column.delimiters
                    .map(
                      (item) =>
                        `${delimiterLabel(item.character)} in ${item.cells} rows (${Math.round(item.share * 100)}%)`,
                    )
                    .join(" · ")}
                </dd>
              </div>
            )}
            {column.overlaps.length > 0 && (
              <div>
                <dt>Shares values with</dt>
                <dd>
                  <ul className="plain-list">
                    {column.overlaps.map((item, index) => (
                      <li key={index}>
                        {item.objectTypeKey
                          ? `${typeName(outline, item.objectTypeKey)} ${
                              item.attributeTypeKey
                                ? (attributeTypeOf(outline, item.attributeTypeKey)?.name ?? item.attributeTypeKey)
                                : "names"
                            } in ${item.workspaceKey}`
                          : `Column ${item.header ?? item.column} of ${item.sheet}`}{" "}
                        <span className="muted">
                          {item.values} values, {Math.round(item.share * 100)}%
                        </span>
                      </li>
                    ))}
                  </ul>
                </dd>
              </div>
            )}
          </dl>
        </section>
      )}
    </div>
  );
}
