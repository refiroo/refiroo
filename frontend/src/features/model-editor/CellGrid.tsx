/**
 * A sheet's cells as a grid, a list's rectangle shaded on it and its header darker (0.10 A8b,
 * D123, D125): the centre shows a list with a row and a column around it, the adjust dialog the
 * area the list may grow into. The grid is a picture; it takes no clicks.
 */

import type { SourceCell, SourceRectangle } from "@/types";
import { columnLetter, columnNumber } from "@/features/model-editor/lists";

export function CellGrid({
  rows,
  top,
  bottom,
  first,
  last,
  list,
  noteRow,
  label,
}: {
  rows: Map<number, Record<string, SourceCell>>;
  top: number;
  bottom: number;
  first: number;
  last: number;
  /** The list's rectangle, shaded. */
  list: SourceRectangle;
  /** The note row under its header, skipped by the load. */
  noteRow?: number | null;
  label: string;
}) {
  const letters = Array.from({ length: Math.max(0, last - first + 1) }, (_, index) => columnLetter(first + index));
  const from = columnNumber(list.block.firstColumn);
  const to = columnNumber(list.block.lastColumn);
  const numbers = Array.from({ length: Math.max(0, bottom - top + 1) }, (_, index) => top + index);
  return (
    <div className="cell-grid-frame">
      <table className="cell-grid" aria-label={label}>
        <thead>
          <tr>
            <th scope="col">
              <span className="visually-hidden">Row</span>
            </th>
            {letters.map((letter) => (
              <th key={letter} scope="col">
                {letter}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {numbers.map((number) => {
            const cells = rows.get(number) ?? {};
            const inRows = number >= list.headerRow && number <= list.block.lastRow;
            return (
              <tr key={number}>
                <th scope="row">{number}</th>
                {letters.map((letter) => {
                  const column = columnNumber(letter);
                  const inside = inRows && column >= from && column <= to;
                  const kind = !inside ? "" : number === list.headerRow ? "header" : number === noteRow ? "note" : "in";
                  const text = cells[letter]?.text ?? "";
                  return (
                    <td
                      key={letter}
                      className={kind ? `cell-${kind}` : undefined}
                      title={text.length > 24 ? text : undefined}
                    >
                      {text}
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
