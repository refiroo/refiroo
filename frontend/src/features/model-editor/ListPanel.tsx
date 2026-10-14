/**
 * A list of a sheet laid out for reading in the editor's centre (0.10 A8b, D123): the titles above
 * it, its cells and note, what loads it, why it was proposed while it is the engine's, and the
 * sheet's cells around it, where a value that is not one (a second header row, a sentence) shows.
 * A loaded list is adjusted or not loaded; a list nothing loads is loaded as a list.
 */

import type { ReactNode } from "react";
import type { ModelDraftOutline, ProfileSource, SourceBlock } from "@/types";
import { InlineError } from "@/ui/InlineError";
import { Notice } from "@/ui/Notice";
import { Skeleton } from "@/ui/Skeleton";
import { StatusPill } from "@/ui/StatusPill";
import { ProposedPill } from "@/features/model-editor/ProposedBecause";
import { CellGrid } from "@/features/model-editor/CellGrid";
import { useCells } from "@/features/model-editor/useCells";
import { typeName } from "@/features/model-editor/outline";
import {
  columnLetter,
  columnNumber,
  LIST_STATUS_LABELS,
  rangeOf,
  rectangleOf,
  rowsOf,
  type ListStatus,
} from "@/features/model-editor/lists";

/** Why nothing loads a list, in words. */
export function notLoadedReason(block: SourceBlock): string {
  if (block.note?.meaning === "free")
    return `The row under its header says ${block.note.text}: answers are typed there, so it was not read as a list. Load it as a list if it is one.`;
  if (!block.rows) return "Its header has nothing under it, so there is nothing to load.";
  return "No source loads it: it was not loaded, or the inference read it otherwise. Load it as a list if it is one.";
}

export function ListPanel({
  sheet,
  block,
  header,
  fileId,
  listSource,
  status,
  outline,
  busy,
  proposed,
  onAdjust,
  onDrop,
  onLoad,
  onShowType,
}: {
  sheet: string;
  block: SourceBlock;
  header: string;
  fileId: string | undefined;
  listSource: ProfileSource | undefined;
  status: ListStatus;
  outline: ModelDraftOutline;
  busy: boolean;
  /** Why the list was proposed, while it is still the engine's (0.10 A6b). */
  proposed?: ReactNode;
  onAdjust: () => void;
  onDrop: () => void;
  onLoad: () => void;
  onShowType: (key: string) => void;
}) {
  const rectangle = rectangleOf(block, listSource);
  const top = Math.max(1, Math.min(rectangle.headerRow, block.headerRow ?? rectangle.headerRow) - 1);
  const bottom = Math.max(rectangle.block.lastRow, block.lastRow) + 1;
  const first = Math.max(1, Math.min(columnNumber(rectangle.block.firstColumn), columnNumber(block.firstColumn)) - 1);
  const last = Math.max(columnNumber(rectangle.block.lastColumn), columnNumber(block.lastColumn)) + 1;
  const cells = useCells(fileId, sheet, `${columnLetter(first)}${top}:${columnLetter(last)}${bottom}`);
  const loaded = status !== "notLoaded" && listSource;
  const rows = rowsOf(block, rectangle);

  return (
    <div className="list-panel">
      <header className="element-header">
        <div className="element-title">
          <p className="eyebrow">List · sheet {sheet}</p>
          <h2 id="element-title">{header}</h2>
          {status === "proposed" ? (
            <ProposedPill />
          ) : (
            <StatusPill tone={status === "loaded" ? "success" : "neutral"}>{LIST_STATUS_LABELS[status]}</StatusPill>
          )}
        </div>
        <div className="element-actions">
          {loaded ? (
            <>
              <button type="button" className="secondary" onClick={onAdjust} disabled={busy}>
                Adjust list…
              </button>
              <button type="button" className="secondary" onClick={onDrop} disabled={busy}>
                Don't load this list
              </button>
            </>
          ) : (
            <button type="button" className="primary" onClick={onLoad} disabled={busy}>
              Load as a list…
            </button>
          )}
        </div>
      </header>

      {status === "proposed" && proposed}
      {!loaded && (
        <Notice tone="warning" title="Not loaded">
          {notLoadedReason(block)}
        </Notice>
      )}

      <dl className="column-facts">
        <div>
          <dt>Under</dt>
          <dd>{block.titles?.length ? block.titles.join(" › ") : "No title above it"}</dd>
        </div>
        <div>
          <dt>Cells</dt>
          <dd>
            <span className="mono">{rangeOf(rectangle)}</span> · header row {rectangle.headerRow} ·{" "}
            {loaded
              ? `${rows} ${rows === 1 ? "row" : "rows"} below it`
              : `${block.rows} ${block.rows === 1 ? "row" : "rows"}`}
          </dd>
        </div>
        <div>
          <dt>Note</dt>
          <dd>{block.note ? `${block.note.text} (row ${block.note.row}), skipped by the load` : "None"}</dd>
        </div>
        <div>
          <dt>Loads</dt>
          <dd>
            {loaded ? (
              <>
                The list type{" "}
                <button type="button" className="link-button" onClick={() => onShowType(listSource.objectTypeKey)}>
                  {typeName(outline, listSource.objectTypeKey)}
                </button>
                , {listSource.key?.field === "name" ? "keyed by name" : "keyed by its key column"}
              </>
            ) : (
              "Nothing"
            )}
          </dd>
        </div>
      </dl>

      <section className="list-panel-cells" aria-labelledby="list-cells-title">
        <h3 id="list-cells-title" className="element-subheading">
          On the sheet
        </h3>
        {cells.error ? (
          <InlineError message={cells.error} onRetry={cells.retry} />
        ) : !cells.range ? (
          <Skeleton lines={5} label={`Reading the cells around ${header}`} />
        ) : (
          <CellGrid
            rows={cells.rows}
            top={top}
            bottom={bottom}
            first={first}
            last={last}
            list={rectangle}
            noteRow={block.note?.row}
            label={`Cells around the list ${header}`}
          />
        )}
        <p className="muted">
          The list's cells with a row and a column around them: shaded, what it loads; darker, its header.
        </p>
      </section>
    </div>
  );
}
