/**
 * Arrow-key movement between the cells of a grid (`role="grid"`), shared by the relation matrix lens
 * (0.8 A4) and the model editor's relationship matrix (0.10 A4a): the cell a key moves to, or
 * `undefined` when the key is not a movement. Rows that page or scroll leave Up and Down to their
 * own window by passing no `rows`.
 */
export function nextGridCell(
  key: string,
  at: { row: number; column: number },
  size: { columns: number; rows?: number },
  ctrl = false,
): { row: number; column: number } | undefined {
  const lastColumn = size.columns - 1;
  const lastRow = (size.rows ?? 1) - 1;
  if (key === "ArrowRight") return { ...at, column: Math.min(lastColumn, at.column + 1) };
  if (key === "ArrowLeft") return { ...at, column: Math.max(0, at.column - 1) };
  if (key === "Home" && !ctrl) return { ...at, column: 0 };
  if (key === "End" && !ctrl) return { ...at, column: lastColumn };
  if (size.rows === undefined) return undefined;
  if (key === "ArrowDown") return { ...at, row: Math.min(lastRow, at.row + 1) };
  if (key === "ArrowUp") return { ...at, row: Math.max(0, at.row - 1) };
  if (key === "Home") return { row: 0, column: 0 };
  if (key === "End") return { row: lastRow, column: lastColumn };
  return undefined;
}
