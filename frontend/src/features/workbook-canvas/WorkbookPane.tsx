/**
 * The workbook's side of the canvas (0.17 PL3b): its sheets, the columns of the open sheet and a
 * compact preview of the sheet's first rows. Columns are chosen as in a file list (a press, Ctrl or
 * Command to add, Shift for a range, Shift with the arrow keys from the keyboard) and dragged, one or
 * the whole selection, onto a list or a field. A column shows what reads it: a mapping, a reading
 * that is on it (rows, blanks filled, headings) and whether it is still as the inference proposed it.
 */

import { useId, useMemo, useRef, type DragEvent, type KeyboardEvent, type MouseEvent } from "react";
import { CellGrid } from "@/features/model-editor/CellGrid";
import { columnLetter, columnNumber } from "@/features/model-editor/lists";
import { usesOf } from "@/features/model-editor/mapping";
import { columnElements } from "@/features/model-editor/proposing";
import { useCells } from "@/features/model-editor/useCells";
import type { DraftProfileDocument, SourceColumn, SourceSheet } from "@/types/sources";
import { ActionMenu, type ActionMenuItem } from "@/ui/ActionMenu";
import { Icon } from "@/ui/Icon";
import { Notice } from "@/ui/Notice";
import { Skeleton } from "@/ui/Skeleton";
import { DRAG_COLUMN, DRAG_COLUMNS, DRAG_FIELD, DRAG_SHEET } from "./CanvasBoard";
import { chosenColumns } from "./canvasModel";
import { addedColumns, readingsOf } from "@/features/model-editor/readings";

/** The first rows of a sheet the preview reads, the header row among them. */
const PREVIEW_ROWS = 8;
const PREVIEW_COLUMNS = 10;

export function SheetPreview({
  fileId,
  sheet,
  headerRow,
  onHeaderRow,
}: {
  fileId: string | undefined;
  sheet: SourceSheet;
  headerRow: number;
  /** Absent when no source reads this sheet: there is no header row to move. */
  onHeaderRow?: (row: number) => void;
}) {
  const first = Math.min(...sheet.blocks.map((block) => columnNumber(block.firstColumn)), 27);
  const last = Math.min(
    Math.max(...sheet.blocks.map((block) => columnNumber(block.lastColumn)), first),
    first + PREVIEW_COLUMNS - 1,
  );
  const bottom = Math.max(2, Math.min(sheet.rows, Math.max(PREVIEW_ROWS, headerRow + 3)));
  const range = `${columnLetter(first)}1:${columnLetter(last)}${bottom}`;
  const cells = useCells(fileId, sheet.name, range);
  const rectangle = useMemo(
    () => ({
      headerRow,
      block: { firstColumn: columnLetter(first), lastColumn: columnLetter(last), lastRow: bottom },
    }),
    [headerRow, first, last, bottom],
  );
  return (
    <section className="canvas-preview" aria-label={`First rows of ${sheet.name}`}>
      <h3 className="canvas-pane-label">First rows</h3>
      {cells.error ? (
        <Notice tone="error">{cells.error}</Notice>
      ) : !cells.range ? (
        <Skeleton lines={3} label={`Reading the first rows of ${sheet.name}`} />
      ) : (
        <CellGrid
          rows={cells.rows}
          top={1}
          bottom={bottom}
          first={first}
          last={last}
          list={rectangle}
          label={`First rows of ${sheet.name}`}
          onHeaderRow={onHeaderRow}
        />
      )}
      <p className="canvas-hint">
        {onHeaderRow
          ? "Press a row number to read that row as the header."
          : "A sheet no object type reads has no header row to move yet."}
      </p>
    </section>
  );
}

export function WorkbookPane({
  sheets,
  sheet,
  onSheet,
  menuForSheet,
  columns,
  profile,
  proposed,
  fileId,
  hasFile,
  error,
  canDrag,
  editable,
  chosen,
  onChosen,
  menuFor,
  onUnpivot,
  onHeaderRow,
  onFieldBack,
  onOpenColumn,
}: {
  sheets: readonly SourceSheet[];
  sheet?: SourceSheet;
  onSheet: (name: string) => void;
  /** A sheet tab's menu: what a drag onto the board does, by menu and keyboard (PP-D75). */
  menuForSheet?: (name: string) => ActionMenuItem[];
  columns: readonly SourceColumn[];
  profile: DraftProfileDocument | null | undefined;
  proposed: ReadonlySet<string>;
  fileId?: string;
  hasFile: boolean;
  error?: string;
  canDrag: boolean;
  editable: boolean;
  /** Chosen columns' headers, in the order they were chosen. */
  chosen: readonly string[];
  onChosen: (headers: string[]) => void;
  menuFor: (column: SourceColumn) => ActionMenuItem[];
  /** The chosen columns to be read as rows: the page asks where and what to call the new columns. */
  onUnpivot: (anchor: HTMLElement) => void;
  onHeaderRow?: (row: number) => void;
  onFieldBack: (event: DragEvent) => void;
  /** A press on a column with no key held: its panel opens in the inspector (CE1). */
  onOpenColumn?: (header: string) => void;
}) {
  const tabs = useId();
  const anchor = useRef<string | undefined>(undefined);
  const named = columns.filter((column) => column.header);
  const order = named.map((column) => column.header ?? "");
  // Where every column of the sheet still reads as proposed, that is said once, above them, not on each.
  const allProposed =
    named.length > 1 &&
    named.every((column) =>
      columnElements(profile, column.sheet, column.header ?? "").some((element) => proposed.has(element)),
    );
  const added = sheet ? addedColumns(profile, sheet.name) : [];
  const sourceOfSheet = (profile?.sources ?? []).find((source) => source.sheet === sheet?.name);

  function press(event: MouseEvent, header: string) {
    const next = chosenColumns(
      chosen,
      order,
      header,
      { shift: event.shiftKey, toggle: event.ctrlKey || event.metaKey },
      anchor.current,
    );
    if (!event.shiftKey) anchor.current = header;
    onChosen(next);
    if (!event.shiftKey && !event.ctrlKey && !event.metaKey) onOpenColumn?.(header);
  }

  function key(event: KeyboardEvent<HTMLButtonElement>, header: string) {
    const step = event.key === "ArrowDown" ? 1 : event.key === "ArrowUp" ? -1 : 0;
    if (event.key === " " && (event.ctrlKey || event.metaKey)) {
      // Ctrl or Command with Space adds or takes away this column, whatever else is chosen.
      event.preventDefault();
      anchor.current = header;
      onChosen(chosenColumns(chosen, order, header, { toggle: true }));
      return;
    }
    if (!step) return;
    event.preventDefault();
    const target = order[order.indexOf(header) + step];
    if (!target) return;
    if (event.shiftKey) {
      anchor.current ??= header;
      onChosen(chosenColumns(chosen, order, target, { shift: true }, anchor.current));
    }
    event.currentTarget
      .closest("ul")
      ?.querySelector<HTMLButtonElement>(`[data-column-pick="${CSS.escape(target)}"]`)
      ?.focus();
  }

  function start(event: DragEvent, column: SourceColumn) {
    const header = column.header ?? "";
    const together =
      chosen.includes(header) && chosen.length > 1 ? order.filter((item) => chosen.includes(item)) : [header];
    event.dataTransfer.setData(DRAG_COLUMN, `${column.sheet}\u0000${header}`);
    if (together.length > 1)
      event.dataTransfer.setData(DRAG_COLUMNS, JSON.stringify({ sheet: column.sheet, headers: together }));
    else if (!chosen.includes(header)) onChosen([header]);
    event.dataTransfer.effectAllowed = "copy";
  }

  return (
    <aside
      className="canvas-pane canvas-workbook"
      aria-label="Workbook"
      onDragOver={(event) => event.dataTransfer.types.includes(DRAG_FIELD) && event.preventDefault()}
      onDrop={onFieldBack}
    >
      <h2 className="canvas-pane-label">Workbook</h2>
      {error && <Notice tone="error">{error}</Notice>}
      {!sheets.length && !error && (
        <p className="canvas-hint">{hasFile ? "Reading the workbook…" : "This draft has no workbook."}</p>
      )}
      <div className="canvas-sheets">
        {/* The tabs sit beside their actions menus, which a tablist may not hold: the list owns its tabs. */}
        <div
          className="visually-hidden"
          role="tablist"
          aria-label="Sheets"
          aria-owns={sheets.map((_, at) => `${tabs}-${at}`).join(" ")}
        />
        {sheets.map((item, at) => (
          <span key={item.name} className="canvas-sheet-item">
            <button
              type="button"
              role="tab"
              id={`${tabs}-${at}`}
              aria-selected={item.name === sheet?.name}
              className={`canvas-sheet${item.name === sheet?.name ? " current" : ""}`}
              draggable={canDrag && editable}
              onDragStart={(event) => {
                event.dataTransfer.setData(DRAG_SHEET, item.name);
                event.dataTransfer.effectAllowed = "copy";
              }}
              onClick={() => onSheet(item.name)}
              title="Drag onto the board to make an object type of its rows"
            >
              {item.name}
              <small>{item.rows.toLocaleString("en-US")}</small>
            </button>
            {editable && menuForSheet && (
              <ActionMenu label={`Actions for ${item.name}`} items={menuForSheet(item.name)} />
            )}
          </span>
        ))}
      </div>
      {sheet && chosen.length > 1 && (
        <div className="canvas-chosen" role="status">
          <span>{chosen.length} columns chosen</span>
          {editable && (
            <button type="button" className="secondary" onClick={(event) => onUnpivot(event.currentTarget)}>
              Read these columns as rows…
            </button>
          )}
          <button type="button" className="secondary" onClick={() => onChosen([])}>
            Clear
          </button>
        </div>
      )}
      {sheet && allProposed && (
        <p className="canvas-hint canvas-all-proposed">
          <span className="canvas-pill canvas-pill-proposed">Proposed</span> Every column is read as proposed.
        </p>
      )}
      {sheet && (
        <ul className="canvas-columns" aria-label={`Columns of ${sheet.name}`}>
          {named.map((column) => {
            const header = column.header ?? "";
            const uses = usesOf(profile, column.sheet, header);
            const ignored = uses.length > 0 && uses.every((use) => use.binding.ignore);
            const mapped = uses.some((use) => !use.binding.ignore);
            const picked = chosen.includes(header);
            const readings = readingsOf(profile, column.sheet, header);
            const asProposed = columnElements(profile, column.sheet, header).some((element) => proposed.has(element));
            return (
              <li
                key={`${column.letter}:${header}`}
                className={`canvas-column${mapped ? " mapped" : ""}${ignored ? " ignored" : ""}${picked ? " chosen" : ""}`}
                draggable={canDrag && editable}
                onDragStart={(event) => start(event, column)}
              >
                <button
                  type="button"
                  className="canvas-column-pick"
                  data-column-pick={header}
                  aria-pressed={picked}
                  onClick={(event) => press(event, header)}
                  onKeyDown={(event) => key(event, header)}
                >
                  <Icon name="grip" size={12} />
                  <span className="canvas-column-text">
                    <span className="canvas-column-name">{header}</span>
                    <small>
                      {ignored
                        ? "left out"
                        : (column.values ?? [])
                            .slice(0, 3)
                            .map((item) => item.value)
                            .join(" · ") || `${column.distinct.toLocaleString("en-US")} values`}
                    </small>
                    {(readings.length > 0 || (asProposed && !allProposed)) && (
                      <span className="canvas-column-marks">
                        {asProposed && !allProposed && (
                          <span className="canvas-pill canvas-pill-proposed">Proposed</span>
                        )}
                        {readings.map((reading) => (
                          <span key={reading.kind} className="canvas-pill canvas-pill-reading">
                            {reading.label}
                          </span>
                        ))}
                      </span>
                    )}
                  </span>
                </button>
                {mapped && <Icon name="check" size={12} label="Mapped" />}
                {editable && <ActionMenu label={`Actions for ${header}`} items={menuFor(column)} />}
              </li>
            );
          })}
          {added.map((item) => (
            <li
              key={`added:${item.header}`}
              className="canvas-column added"
              draggable={canDrag && editable}
              onDragStart={(event) => {
                event.dataTransfer.setData(DRAG_COLUMN, `${sheet.name}\u0000${item.header}`);
                event.dataTransfer.effectAllowed = "copy";
              }}
            >
              <span className="canvas-column-pick" role="group" aria-label={`${item.header}, a column a reading adds`}>
                <Icon name="grip" size={12} />
                <span className="canvas-column-text">
                  <span className="canvas-column-name">{item.header}</span>
                  <small>{item.label}</small>
                </span>
              </span>
              {usesOf(profile, sheet.name, item.header).some((use) => !use.binding.ignore) && (
                <Icon name="check" size={12} label="Mapped" />
              )}
            </li>
          ))}
        </ul>
      )}
      {sheet && (
        <SheetPreview
          key={sheet.name}
          fileId={fileId}
          sheet={sheet}
          headerRow={sourceOfSheet?.headerRow ?? sheet.headerRow ?? 1}
          onHeaderRow={editable ? onHeaderRow : undefined}
        />
      )}
      <p className="canvas-hint">
        {canDrag
          ? "Drag a column, or the columns you chose, onto an object type or one of its attributes, or onto the empty board for an object type of its values. Drag an attribute back here to leave it out."
          : "Use a column's ⋯ menu to add it to an object type, make an object type of its values or leave it out."}
      </p>
    </aside>
  );
}
