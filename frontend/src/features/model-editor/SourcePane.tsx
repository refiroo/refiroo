/**
 * The source pane of the model editor (0.10 A5b, D84): the draft's source file, its sheets as tabs
 * and each sheet's columns with their status (the key, mapped, not mapped, ignored, with an issue;
 * a model description's columns read Describes the model, 0.10 A7)
 * and statistics from the file's profile (A3). Selecting a column shows its mapping in the centre;
 * a type selected in the model pane marks the columns that feed it.
 *
 * The columns are one `role="listbox"` with one tab stop: Up and Down move, Home and End jump,
 * Enter selects, Shift+F10 or the context-menu key opens Map to…. A column is dragged onto the
 * model pane, with mouse or pen, to map it there.
 */

import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import type { DraftProfile, EditorSelection, SourceColumn, SourceSheet } from "@/types";
import { ActionMenu } from "@/ui/ActionMenu";
import { InlineError } from "@/ui/InlineError";
import { Notice } from "@/ui/Notice";
import { Skeleton } from "@/ui/Skeleton";
import { Tabs } from "@/ui/Tabs";
import type { DraftSource } from "@/features/model-editor/useDraftSource";
import {
  columnId,
  columnState,
  issuesByColumn,
  STATUS_LABELS,
  statisticsWords,
  type ColumnStatus,
} from "@/features/model-editor/mapping";
import { columnElements } from "@/features/model-editor/proposing";

const NONE: ReadonlySet<string> = new Set();

/** The data a dragged column carries: its sheet and header. */
export const DRAG_COLUMN = "application/x-rdm-column";

export function SourcePane({
  source,
  selection,
  linked,
  canDrag,
  sheetNames,
  onSelect,
  onMap,
  onIgnoreSheet,
  proposed = NONE,
  describing = NONE,
}: {
  source: DraftSource;
  selection: EditorSelection;
  /** Columns (`columnId`) that feed the type selected in the model pane. */
  linked: Set<string>;
  /** The elements still as the inference proposed them (0.10 A6b): their columns read Proposed. */
  proposed?: ReadonlySet<string>;
  /** Sheets read as a model description (0.10 A7): their types came from it, nothing loads from them. */
  describing?: ReadonlySet<string>;
  canDrag: boolean;
  /** Each loaded sheet's sources, in words: "Loads Item · key Item code". */
  sheetNames: (sheet: string) => string;
  onSelect: (selection: EditorSelection) => void;
  onMap: (sheet: string, header: string) => void;
  onIgnoreSheet: (sheet: string) => void;
}) {
  const file = source.profile?.sourceFile;
  const selectedSheet = selection.show === "column" ? selection.sheet : undefined;
  const [chosenSheet, setChosenSheet] = useState<string>();
  const sheets = source.sheets;
  const shown = sheets.find((item) => item.name === (chosenSheet ?? selectedSheet))?.name ?? sheets[0]?.name;
  const { loadColumns } = source;
  useEffect(() => {
    if (shown) loadColumns(shown);
  }, [shown, loadColumns]);

  if (!file) return null;
  const state = file.profile;
  return (
    <section className="model-editor-source" aria-label="Source">
      <header className="source-pane-head">
        <span className="nav-label">Source</span>
        <span className="source-pane-file" title={file.name}>
          {file.name}
        </span>
      </header>
      {source.error && <InlineError message={source.error} onRetry={source.retry} />}
      {state === "queued" || state === "running" ? (
        <div className="source-pane-state" role="status">
          <p>Profiling {file.name}: reading every sheet and column…</p>
          <Skeleton lines={5} label="Profiling the workbook" />
        </div>
      ) : state !== "completed" ? (
        <Notice tone="error" title="The workbook was not profiled">
          {source.file?.profile.error?.message ?? `Profiling ended ${state}.`} Upload it again from the ⋯ menu.
        </Notice>
      ) : (
        <Tabs
          label="Sheets"
          selected={shown}
          onChange={setChosenSheet}
          tabs={sheets.map((sheet) => ({
            id: sheet.name,
            label: `${sheet.name} · ${sheet.rows.toLocaleString()}`,
            content: (
              <SheetColumns
                sheet={sheet}
                columns={source.columns(sheet.name)}
                profile={source.profile}
                proposed={proposed}
                describes={describing.has(sheet.name)}
                selection={selection}
                linked={linked}
                canDrag={canDrag}
                loads={sheetNames(sheet.name)}
                onSelect={(header) => {
                  setChosenSheet(sheet.name);
                  onSelect({ show: "column", sheet: sheet.name, key: header });
                }}
                onMap={(header) => onMap(sheet.name, header)}
                onIgnoreSheet={() => onIgnoreSheet(sheet.name)}
              />
            ),
          }))}
        />
      )}
      <p className="source-pane-hint muted">Drag a column onto the model, or use Map to… in its menu.</p>
    </section>
  );
}

function SheetColumns({
  sheet,
  columns,
  profile,
  proposed,
  describes,
  selection,
  linked,
  canDrag,
  loads,
  onSelect,
  onMap,
  onIgnoreSheet,
}: {
  sheet: SourceSheet;
  columns: SourceColumn[] | undefined;
  profile: DraftProfile | undefined;
  proposed: ReadonlySet<string>;
  describes: boolean;
  selection: EditorSelection;
  linked: Set<string>;
  canDrag: boolean;
  loads: string;
  onSelect: (header: string) => void;
  onMap: (header: string) => void;
  onIgnoreSheet: () => void;
}) {
  const list = useRef<HTMLUListElement>(null);
  const [focused, setFocused] = useState<string>();
  const issues = issuesByColumn(profile);
  const ignored = Boolean(profile?.profile?.ignoredSheets?.includes(sheet.name));
  const rows = (columns ?? []).filter((column) => column.header);
  const selected = selection.show === "column" && selection.sheet === sheet.name ? selection.key : undefined;
  const tabStop = rows.find((column) => column.header === (focused ?? selected))?.header ?? rows[0]?.header;

  const focus = (index: number) => {
    const column = rows[Math.min(rows.length - 1, Math.max(0, index))];
    if (!column?.header) return;
    setFocused(column.header);
    list.current?.querySelector<HTMLElement>(`[data-column="${CSS.escape(column.header)}"]`)?.focus();
  };
  function onKeyDown(event: KeyboardEvent<HTMLElement>, index: number, header: string) {
    if ((event.key === "F10" && event.shiftKey) || event.key === "ContextMenu") {
      event.preventDefault();
      onSelect(header);
      onMap(header);
      return;
    }
    const moves: Record<string, number> = { ArrowDown: index + 1, ArrowUp: index - 1, Home: 0, End: rows.length - 1 };
    if (event.key in moves) {
      event.preventDefault();
      focus(moves[event.key]);
    } else if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onSelect(header);
    }
  }

  return (
    <div className="source-sheet">
      <div className="source-sheet-head">
        <span className="muted">
          {describes && ignored
            ? "Describes the model: its fields and lists were read from it, nothing loads from it"
            : ignored
              ? "Ignored: nothing loads from this sheet"
              : loads}{" "}
          · header row {sheet.headerRow ?? "—"}
        </span>
        <ActionMenu
          label={`Sheet ${sheet.name}`}
          tooltip="Sheet actions"
          items={[{ id: "ignore", label: "Ignore this sheet", disabled: ignored, onAction: onIgnoreSheet }]}
        />
      </div>
      {!columns ? (
        <Skeleton lines={6} label={`Reading the columns of ${sheet.name}`} />
      ) : (
        <ul className="source-columns" role="listbox" aria-label={`Columns of ${sheet.name}`} ref={list}>
          {rows.map((column, index) => {
            const header = column.header ?? "";
            const state = columnState(profile, issues, sheet.name, header);
            const engines =
              (state.status === "mapped" || state.status === "key") &&
              columnElements(profile?.profile, sheet.name, header).some((element) => proposed.has(element));
            const status: ColumnStatus =
              describes && ignored && (state.status === "unmapped" || state.status === "ignored")
                ? "describes"
                : ignored && state.status === "unmapped"
                  ? "ignored"
                  : engines
                    ? "proposed"
                    : state.status;
            return (
              <li
                key={`${column.block}:${column.letter}`}
                data-column={header}
                role="option"
                aria-selected={header === selected}
                aria-description={linked.has(columnId(sheet.name, header)) ? "Feeds the selected type" : undefined}
                tabIndex={header === tabStop ? 0 : -1}
                className={[
                  "source-column",
                  header === selected ? "selected" : "",
                  linked.has(columnId(sheet.name, header)) ? "linked" : "",
                ]
                  .filter(Boolean)
                  .join(" ")}
                draggable={canDrag}
                onDragStart={(event) => {
                  event.dataTransfer.setData(DRAG_COLUMN, columnId(sheet.name, header));
                  event.dataTransfer.effectAllowed = "link";
                }}
                onFocus={() => setFocused(header)}
                onClick={() => onSelect(header)}
                onContextMenu={(event) => {
                  event.preventDefault();
                  onSelect(header);
                  onMap(header);
                }}
                onKeyDown={(event) => onKeyDown(event, index, header)}
              >
                <span className={`source-dot status-${status}`} aria-hidden="true" />
                <span className="source-column-text">
                  <span className="source-column-name">
                    {header} <span className="source-column-letter">{column.letter}</span>
                  </span>
                  <span className="source-column-stats">{statisticsWords(column)}</span>
                </span>
                <span className={`source-column-status status-${status}`}>{STATUS_LABELS[status]}</span>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
