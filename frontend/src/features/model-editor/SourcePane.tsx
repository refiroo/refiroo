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
import { count, counted } from "@/lib/count";
import type {
  DraftProfile,
  EditorSelection,
  ModelDiagnostic,
  ModelDraftOutline,
  SourceBlock,
  SourceColumn,
  SourceSheet,
} from "@/types";
import { EditableText } from "@/features/model-editor/EditableText";
import { PROFILE_KEY_MISMATCH, UseFreeKey } from "@/features/model-editor/ProfileKeyConflict";
import type { StepOutcome } from "@/features/model-editor/OperationDialog";
import { ActionMenu } from "@/ui/ActionMenu";
import { Icon } from "@/ui/Icon";
import { InlineError } from "@/ui/InlineError";
import { Notice } from "@/ui/Notice";
import { ReadingMarks } from "@/features/model-editor/ReadingEntries";
import { Skeleton } from "@/ui/Skeleton";
import { StatusPill } from "@/ui/StatusPill";
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
import { columnElements } from "@/model/proposing";
import {
  columnNumber,
  LIST_STATUS_LABELS,
  listColumns,
  listHeader,
  listStatus,
  listWords,
  rangeOf,
  rectangleOf,
  sourceOfList,
  type ListStatus,
} from "@/features/model-editor/lists";

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
  outline,
  onSetProfile,
}: {
  source: DraftSource;
  /** With `onSetProfile`: the profile's key and name, edited in place (a step each). */
  outline?: ModelDraftOutline;
  onSetProfile?: (patch: { key?: string; name?: string }) => Promise<StepOutcome>;
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
      {outline && source.profile?.profile && (
        <ProfileIdentity profile={source.profile} outline={outline} onSet={onSetProfile} />
      )}
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
            label: `${sheet.name} · ${count(sheet.rows)}`,
            content: sheet.laidOut ? (
              <SheetLists
                sheet={sheet}
                columns={source.columns(sheet.name)}
                profile={source.profile}
                proposed={proposed}
                selection={selection}
                canDrag={canDrag}
                onSelect={(next) => {
                  setChosenSheet(sheet.name);
                  onSelect(next);
                }}
                onMap={(header) => onMap(sheet.name, header)}
                onIgnoreSheet={() => onIgnoreSheet(sheet.name)}
              />
            ) : (
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

/**
 * The draft's import profile key and name, where the editor shows the source. The key is what a
 * stored profile is found by, so one that belongs to another model is a conflict: Use '…' sets the
 * key the engine found free (`setProfile`, an undoable step).
 */
function ProfileIdentity({
  profile,
  outline,
  onSet,
}: {
  profile: DraftProfile;
  outline: ModelDraftOutline;
  /** Absent while the editor is paused: the values are read, not edited. */
  onSet?: (patch: { key?: string; name?: string }) => Promise<StepOutcome>;
}) {
  const document = profile.profile as NonNullable<DraftProfile["profile"]>;
  const conflict = profile.diagnostics.some((item) => item.code === PROFILE_KEY_MISMATCH);
  return (
    <dl className="source-pane-profile" aria-label="Import profile">
      <div id="profile-key-field">
        <dt>Profile key</dt>
        <dd>
          {onSet ? (
            <EditableText
              value={document.key}
              label="Profile key"
              outline={outline}
              onSave={(key) => onSet({ key })}
              after={
                conflict && profile.freeKey ? (
                  <UseFreeKey freeKey={profile.freeKey} onUse={() => void onSet({ key: profile.freeKey as string })} />
                ) : undefined
              }
            />
          ) : (
            <span>{document.key}</span>
          )}
        </dd>
      </div>
      <div>
        <dt>Profile name</dt>
        <dd>
          {onSet ? (
            <EditableText
              value={document.name}
              label="Profile name"
              outline={outline}
              onSave={(name) => onSet({ name })}
            />
          ) : (
            <span>{document.name}</span>
          )}
        </dd>
      </div>
    </dl>
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
        <ul className="source-columns list-reset" role="listbox" aria-label={`Columns of ${sheet.name}`} ref={list}>
          {rows.map((column, index) => {
            const header = column.header ?? "";
            const status = columnDisplayStatus(profile, issues, proposed, sheet.name, header, { describes, ignored });
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
                <ColumnRowBody column={column} status={status} profile={profile} />
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

/** How a column reads in the pane: its mapping's status, Proposed while the engine's (0.10 A6b),
 * Ignored or Describes the model on a sheet left out (0.10 A7). */
function columnDisplayStatus(
  profile: DraftProfile | undefined,
  issues: Map<string, ModelDiagnostic[]>,
  proposed: ReadonlySet<string>,
  sheet: string,
  header: string,
  { describes = false, ignored = false }: { describes?: boolean; ignored?: boolean } = {},
): ColumnStatus {
  const state = columnState(profile, issues, sheet, header);
  const engines =
    (state.status === "mapped" || state.status === "key") &&
    columnElements(profile?.profile, sheet, header).some((element) => proposed.has(element));
  return describes && ignored && (state.status === "unmapped" || state.status === "ignored")
    ? "describes"
    : ignored && state.status === "unmapped"
      ? "ignored"
      : engines
        ? "proposed"
        : state.status;
}

/** A column's row in the pane: its status dot, header and letter, statistics and status word. */
function ColumnRowBody({
  column,
  status,
  profile,
}: {
  column: SourceColumn;
  status: ColumnStatus;
  profile: DraftProfile | undefined;
}) {
  return (
    <>
      <span className={`source-dot status-${status}`} aria-hidden="true" />
      <span className="source-column-text">
        <span className="source-column-name">
          {column.header} <span className="source-column-letter">{column.letter}</span>
        </span>
        <span className="source-column-stats">{statisticsWords(column)}</span>
        <ReadingMarks profile={profile?.profile} sheet={column.sheet} header={column.header ?? ""} />
      </span>
      <span className={`source-column-status status-${status}`}>{STATUS_LABELS[status]}</span>
    </>
  );
}

const LIST_TONES: Record<ListStatus, "proposed" | "success" | "neutral"> = {
  proposed: "proposed",
  loaded: "success",
  notLoaded: "neutral",
};

type TreeItem =
  | { id: string; kind: "list"; block: SourceBlock; header: string; status: ListStatus; range: string; words: string }
  | { id: string; kind: "column"; block: SourceBlock; column: SourceColumn; status: ColumnStatus };

/**
 * A sheet laid out for reading, list by list (0.10 A8b, D122): its lists under their innermost
 * title, each with its range, rows, note and status; the open list's columns under it, as the
 * column list shows them. One `role="tree"` with one tab stop: Up and Down move, Right opens a list
 * or enters it, Left closes it or returns to it, Home and End jump, Enter selects, Shift+F10 or the
 * context-menu key on a column opens Map to…. Columns are dragged onto the model as in the list.
 */
function SheetLists({
  sheet,
  columns,
  profile,
  proposed,
  selection,
  canDrag,
  onSelect,
  onMap,
  onIgnoreSheet,
}: {
  sheet: SourceSheet;
  columns: SourceColumn[] | undefined;
  profile: DraftProfile | undefined;
  proposed: ReadonlySet<string>;
  selection: EditorSelection;
  canDrag: boolean;
  onSelect: (selection: EditorSelection) => void;
  onMap: (header: string) => void;
  onIgnoreSheet: () => void;
}) {
  const tree = useRef<HTMLDivElement>(null);
  const selectedList = selection.show === "list" && selection.sheet === sheet.name ? selection.block : undefined;
  const [open, setOpen] = useState<number | undefined>(selectedList);
  const [focused, setFocused] = useState<string>();
  const issues = issuesByColumn(profile);
  const ignored = Boolean(profile?.profile?.ignoredSheets?.includes(sheet.name));

  // In reading order, row by row and left to right; the profile lists them column run by run.
  const ordered = [...sheet.blocks].sort(
    (a, b) => (a.headerRow ?? 0) - (b.headerRow ?? 0) || columnNumber(a.firstColumn) - columnNumber(b.firstColumn),
  );
  const lists = ordered.map((block) => {
    const loads = sourceOfList(profile?.profile, sheet.name, block);
    const status = listStatus(loads, proposed);
    // The range the list's source loads, which Adjust list… may have changed (D125).
    const rectangle = status === "notLoaded" ? undefined : rectangleOf(block, loads);
    return {
      block,
      header: listHeader(block, columns),
      status,
      range: rangeOf(rectangle ?? rectangleOf(block, undefined)),
      words: listWords(block, rectangle),
    };
  });
  // Each innermost title's lists together, the titles in the order their first list is read.
  const byTitle = new Map<string, TreeItem[]>();
  for (const list of lists) {
    const title = list.block.titles?.at(-1) ?? "";
    if (!byTitle.has(title)) byTitle.set(title, []);
    const items = byTitle.get(title) as TreeItem[];
    items.push({ id: `list:${list.block.index}`, kind: "list", ...list });
    if (open === list.block.index)
      for (const column of listColumns(list.block, columns))
        items.push({
          id: `column:${list.block.index}:${column.letter}`,
          kind: "column",
          block: list.block,
          column,
          status: columnDisplayStatus(profile, issues, proposed, sheet.name, column.header ?? "", { ignored }),
        });
  }
  const sections = [...byTitle].map(([title, items]) => ({ title, items }));
  const flat = sections.flatMap((section) => section.items);
  const isSelected = (item: TreeItem) =>
    item.kind === "list"
      ? selectedList === item.block.index
      : selection.show === "column" && selection.sheet === sheet.name && selection.key === item.column.header;
  const tabStop = flat.find((item) => item.id === focused)?.id ?? flat.find(isSelected)?.id ?? flat[0]?.id;
  const loaded = lists.filter((list) => list.status !== "notLoaded").length;

  const focus = (id: string | undefined) => {
    if (!id) return;
    setFocused(id);
    requestAnimationFrame(() => tree.current?.querySelector<HTMLElement>(`[data-item="${CSS.escape(id)}"]`)?.focus());
  };
  const choose = (item: TreeItem) => {
    if (item.kind === "list") {
      setOpen(item.block.index);
      onSelect({ show: "list", sheet: sheet.name, block: item.block.index });
    } else if (item.column.header) onSelect({ show: "column", sheet: sheet.name, key: item.column.header });
  };
  function onKeyDown(event: KeyboardEvent<HTMLElement>, item: TreeItem) {
    const index = flat.findIndex((other) => other.id === item.id);
    const header = item.kind === "column" ? (item.column.header ?? "") : "";
    if (item.kind === "column" && ((event.key === "F10" && event.shiftKey) || event.key === "ContextMenu")) {
      event.preventDefault();
      choose(item);
      onMap(header);
      return;
    }
    const moves: Record<string, number> = { ArrowDown: index + 1, ArrowUp: index - 1, Home: 0, End: flat.length - 1 };
    if (event.key in moves) {
      event.preventDefault();
      focus(flat[Math.min(flat.length - 1, Math.max(0, moves[event.key]))]?.id);
    } else if (event.key === "ArrowRight" && item.kind === "list") {
      event.preventDefault();
      if (open !== item.block.index) setOpen(item.block.index);
      else focus(flat[index + 1]?.kind === "column" ? flat[index + 1].id : undefined);
    } else if (event.key === "ArrowLeft") {
      event.preventDefault();
      if (item.kind === "column") focus(`list:${item.block.index}`);
      else if (open === item.block.index) setOpen(undefined);
    } else if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      choose(item);
    }
  }

  return (
    <div className="source-sheet">
      <div className="source-sheet-head">
        <span className="muted">
          {ignored
            ? "Ignored: nothing loads from this sheet"
            : `Laid out for reading · ${counted(lists.length, "list")}, ${loaded} loaded`}
        </span>
        <ActionMenu
          label={`Sheet ${sheet.name}`}
          tooltip="Sheet actions"
          items={[{ id: "ignore", label: "Ignore this sheet", disabled: ignored, onAction: onIgnoreSheet }]}
        />
      </div>
      {!columns ? (
        <Skeleton lines={6} label={`Reading the lists of ${sheet.name}`} />
      ) : (
        <div className="source-lists" role="tree" aria-label={`Lists of ${sheet.name}`} ref={tree}>
          {sections.map((section, sectionIndex) => (
            <div key={sectionIndex} role="group" aria-label={section.title || "Without a title"}>
              {section.title && (
                <div className="source-list-title" aria-hidden="true">
                  {section.title}
                </div>
              )}
              {section.items.map((item) =>
                item.kind === "list" ? (
                  <div
                    key={item.id}
                    data-item={item.id}
                    role="treeitem"
                    aria-level={1}
                    aria-expanded={open === item.block.index}
                    aria-selected={isSelected(item)}
                    tabIndex={item.id === tabStop ? 0 : -1}
                    className={["source-list", isSelected(item) ? "selected" : ""].filter(Boolean).join(" ")}
                    onFocus={() => setFocused(item.id)}
                    onClick={() => {
                      if (selectedList === item.block.index)
                        setOpen(open === item.block.index ? undefined : item.block.index);
                      else choose(item);
                    }}
                    onKeyDown={(event) => onKeyDown(event, item)}
                  >
                    <Icon name={open === item.block.index ? "chevron-down" : "chevron-right"} size={12} />
                    <span className="source-column-text">
                      <span className="source-column-name">
                        {item.header} <span className="source-column-letter">{item.range}</span>
                      </span>
                      <span className="source-column-stats">{item.words}</span>
                    </span>
                    <StatusPill tone={LIST_TONES[item.status]}>{LIST_STATUS_LABELS[item.status]}</StatusPill>
                  </div>
                ) : (
                  <div
                    key={item.id}
                    data-item={item.id}
                    data-column={item.column.header ?? ""}
                    role="treeitem"
                    aria-level={2}
                    aria-selected={isSelected(item)}
                    tabIndex={item.id === tabStop ? 0 : -1}
                    className={["source-column", "in-list", isSelected(item) ? "selected" : ""]
                      .filter(Boolean)
                      .join(" ")}
                    draggable={canDrag}
                    onDragStart={(event) => {
                      event.dataTransfer.setData(DRAG_COLUMN, columnId(sheet.name, item.column.header ?? ""));
                      event.dataTransfer.effectAllowed = "link";
                    }}
                    onFocus={() => setFocused(item.id)}
                    onClick={() => choose(item)}
                    onContextMenu={(event) => {
                      event.preventDefault();
                      choose(item);
                      onMap(item.column.header ?? "");
                    }}
                    onKeyDown={(event) => onKeyDown(event, item)}
                  >
                    <ColumnRowBody column={item.column} status={item.status} profile={profile} />
                  </div>
                ),
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
