/**
 * Adjust list… and Load as a list… (0.10 A8b, D125–D128): the rows and columns a list loads, set by
 * four fields over the sheet's cells, the outline following them. Adjusting sends one setSource
 * (the columns keep their bindings on their letters, D126, and the list may take the new header's
 * name); loading asks the engine to read the rectangle as a list and sends what it answers as one
 * step. The fields are the keyboard and phone path; the grid is the picture.
 */

import { useState, type FormEvent } from "react";
import { api } from "@/api/client";
import { errorMessage } from "@/api/errors";
import { counted } from "@/lib/count";
import type { DraftOperation, ProfileSource, SourceBlock, SourceRectangle } from "@/types";
import { FormField } from "@/ui/FormField";
import { InlineError } from "@/ui/InlineError";
import { Modal } from "@/ui/Modal";
import { Notice } from "@/ui/Notice";
import { Skeleton } from "@/ui/Skeleton";
import { CellGrid } from "@/features/model-editor/CellGrid";
import { useCells } from "@/features/model-editor/useCells";
import {
  adjustOperations,
  columnLetter,
  columnNumber,
  rangeOf,
  rectangleOf,
  rowsOf,
} from "@/features/model-editor/lists";

/** Rows shown above and below the list, and columns beside it; at most this many rows in all. */
const MARGIN_ROWS = 4;
const MARGIN_COLUMNS = 2;
const MOST_ROWS = 200;

export function AdjustListDialog({
  mode,
  draftId,
  fileId,
  sheet,
  header,
  block,
  listSource,
  lastColumn,
  send,
  onDone,
  onClose,
}: {
  mode: "adjust" | "load";
  draftId: string;
  fileId: string | undefined;
  sheet: string;
  header: string;
  block: SourceBlock;
  listSource: ProfileSource | undefined;
  /** The sheet's last column holding a cell, by number. */
  lastColumn: number;
  /** Sends the operations as one step; throws what the server refused. */
  send: (operations: DraftOperation[]) => Promise<unknown>;
  onDone: () => void;
  onClose: () => void;
}) {
  const start = rectangleOf(block, mode === "adjust" ? listSource : undefined);
  const [headerRow, setHeaderRow] = useState(start.headerRow);
  const [lastRow, setLastRow] = useState(start.block.lastRow);
  const [firstColumn, setFirstColumn] = useState(start.block.firstColumn);
  const [lastLetter, setLastLetter] = useState(start.block.lastColumn);
  const [rename, setRename] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");

  const rectangle: SourceRectangle = { headerRow, block: { firstColumn, lastColumn: lastLetter, lastRow } };
  const from = columnNumber(firstColumn);
  const to = columnNumber(lastLetter);
  const top = Math.max(1, Math.min(headerRow, start.headerRow) - MARGIN_ROWS);
  const bottom = Math.min(Math.max(lastRow, start.block.lastRow) + MARGIN_ROWS, top + MOST_ROWS - 1);
  const left = Math.max(1, Math.min(from, columnNumber(start.block.firstColumn)) - MARGIN_COLUMNS);
  const right = Math.min(Math.max(lastColumn, to), Math.max(to, columnNumber(start.block.lastColumn)) + MARGIN_COLUMNS);
  const cells = useCells(fileId, sheet, `${columnLetter(left)}${top}:${columnLetter(right)}${bottom}`);
  const letters = Array.from({ length: Math.max(0, lastColumn + MARGIN_COLUMNS) }, (_, index) =>
    columnLetter(index + 1),
  );

  const wrong =
    lastRow < headerRow
      ? "The last row is above the header row."
      : to < from
        ? "The last column is before the first."
        : "";
  const noteRow = block.note && block.note.row > headerRow && block.note.row <= lastRow ? block.note.row : undefined;
  let rows = 0;
  for (const [number, row] of cells.rows) {
    if (number <= headerRow || number > lastRow || number === noteRow) continue;
    if (Object.keys(row).some((letter) => columnNumber(letter) >= from && columnNumber(letter) <= to)) rows += 1;
  }
  const before = rowsOf(block, start);
  // A rectangle with nothing under its header (a free field's note alone) has nothing to load (D128).
  const empty = Boolean(cells.range) && rows === 0;
  const newHeader = cells.rows.get(headerRow)?.[firstColumn]?.text ?? "";
  const moved = mode === "adjust" && headerRow !== start.headerRow;
  const oldHeaders = cells.rows.get(start.headerRow) ?? {};
  const follows = (listSource?.columns ?? [])
    .map((binding) => binding.column)
    .filter((column): column is string => Boolean(column))
    .map((column) => {
      const letter = Object.entries(oldHeaders).find(([, cell]) => cell.text.trim() === column)?.[0];
      if (!letter) return `${column} stays`;
      const number = columnNumber(letter);
      const next = cells.rows.get(headerRow)?.[letter]?.text;
      return number < from || number > to || !next
        ? `${letter} ${column} is no longer mapped`
        : `${letter} ${column} → ${next.trim()}`;
    });

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (wrong || pending) return;
    setPending(true);
    setError("");
    try {
      if (mode === "adjust" && listSource) {
        await send(
          adjustOperations(listSource, rectangle, moved && rename && newHeader ? newHeader.trim() : undefined),
        );
      } else {
        const proposal = await api.proposeList(draftId, { sheet, ...rectangle });
        await send(proposal.operations);
      }
      onDone();
    } catch (cause) {
      setError(errorMessage(cause));
      setPending(false);
    }
  }

  const title = mode === "adjust" ? `Adjust the list ${header}` : `Load ${header} as a list`;
  return (
    <Modal
      title={title}
      eyebrow={mode === "adjust" ? "Adjust list" : "Load as a list"}
      icon="table"
      description={
        mode === "adjust"
          ? "Set the rows and columns the list loads. Its columns keep what they load."
          : "Set the rows and columns, and the engine reads them as it reads every list of a sheet laid out for reading."
      }
      size="wide"
      busy={pending}
      dirty={rangeOf(rectangle) !== rangeOf(start)}
      onClose={onClose}
    >
      <form className="adjust-list" onSubmit={(event) => void submit(event)}>
        <div className="adjust-list-fields">
          <FormField label="Header row">
            {(control) => (
              <input
                {...control}
                type="number"
                min={1}
                value={headerRow}
                onChange={(event) => setHeaderRow(Math.max(1, Number(event.target.value) || 1))}
              />
            )}
          </FormField>
          <FormField label="Last row">
            {(control) => (
              <input
                {...control}
                type="number"
                min={1}
                value={lastRow}
                onChange={(event) => setLastRow(Math.max(1, Number(event.target.value) || 1))}
              />
            )}
          </FormField>
          <FormField label="First column">
            {(control) => (
              <select {...control} value={firstColumn} onChange={(event) => setFirstColumn(event.target.value)}>
                {letters.map((letter) => (
                  <option key={letter}>{letter}</option>
                ))}
              </select>
            )}
          </FormField>
          <FormField label="Last column">
            {(control) => (
              <select {...control} value={lastLetter} onChange={(event) => setLastLetter(event.target.value)}>
                {letters.map((letter) => (
                  <option key={letter}>{letter}</option>
                ))}
              </select>
            )}
          </FormField>
          <output className="adjust-list-range mono" aria-label="Range">
            {rangeOf(rectangle)}
          </output>
        </div>
        {cells.error ? (
          <InlineError message={cells.error} onRetry={cells.retry} />
        ) : !cells.range ? (
          <Skeleton lines={8} label={`Reading the cells of ${sheet}`} />
        ) : (
          <CellGrid
            rows={cells.rows}
            top={top}
            bottom={bottom}
            first={left}
            last={right}
            list={rectangle}
            noteRow={noteRow}
            label={`Cells of ${sheet}, the list outlined`}
          />
        )}
        <div className="adjust-list-summary" role="status">
          {wrong ? (
            <span>{wrong}</span>
          ) : mode === "adjust" ? (
            <span>
              {counted(rows, "row")} below the header (now {before})
              {firstColumn !== start.block.firstColumn || lastLetter !== start.block.lastColumn
                ? "; a column added is not mapped until you map it"
                : ""}
              . The dry run follows.
            </span>
          ) : empty ? (
            <span>
              Nothing under the header {newHeader || "(empty)"}
              {noteRow ? " but its note" : ""}: there is nothing to load. Take in the rows that hold the list's values.
            </span>
          ) : (
            <span>
              {counted(rows, "row")} below the header {newHeader || "(empty)"}
              {noteRow ? ", the note row skipped" : ""}. A list type keyed by name, yours since you asked for it.
            </span>
          )}
          {moved && (
            <>
              <span className="muted">
                The header moves to row {headerRow}. Each column keeps its binding on its letter: {follows.join(", ")}.
              </span>
              <label className="checkbox">
                <input type="checkbox" checked={rename} onChange={(event) => setRename(event.target.checked)} />
                Name the list after the new header ({newHeader || "empty"})
              </label>
            </>
          )}
        </div>
        {error && (
          <Notice tone="error" title={mode === "adjust" ? "Not adjusted" : "Not loaded"}>
            {error}
          </Notice>
        )}
        <div className="dialog-actions">
          <button type="button" className="secondary" onClick={onClose} disabled={pending}>
            Cancel
          </button>
          <button type="submit" className="primary" disabled={pending || Boolean(wrong) || (mode === "load" && empty)}>
            {pending ? (mode === "adjust" ? "Applying…" : "Loading…") : mode === "adjust" ? "Save" : "Load as a list"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
